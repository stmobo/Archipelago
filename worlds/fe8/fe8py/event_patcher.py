from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Iterator, List, Optional, Set, Tuple, Union

from .data_structs.event import Event
from .linker import (
    SECTION_TYPE_ROM,
    SYM_TYPE_DATA,
    Linker,
    Section,
    Symbol,
    relocation_types,
)
from .rom import ROM
from .rom_file import ensure_file_offset, ensure_rom_address

if TYPE_CHECKING:
    from .data_structs.chapter import EventCondition


def _event_sym_name(evt_addr: Union[int, Tuple[bool, int]]) -> str:
    if isinstance(evt_addr, int):
        return f"__Event_{evt_addr:08X}"
    elif evt_addr[0]:
        return f"__Event_{evt_addr[1]:08X}"
    else:
        return f"__Event_New{evt_addr[1]}"


def _encode_arithmetic_slots(dest: int, src_a: int, src_b: int) -> int:
    return (
        (_ensure_valid_slot(src_a) << 8)
        | (_ensure_valid_slot(src_b) << 4)
        | _ensure_valid_slot(dest)
    )


def _ensure_valid_slot(slot: int) -> int:
    if not isinstance(slot, int):
        raise TypeError(f"Expected int for slot, got {type(slot).__name__}")
    if (slot < 0) or (slot >= 0xE):
        raise ValueError(f"Invalid event slot {slot:#X}")
    return slot


class EventPatches:
    linker: Linker
    rom: ROM

    events: Dict[Tuple[bool, int], EventPatcher]  # address => patcher
    conditions: Dict[int, EventCondition]  # address => condition
    start_events: Dict[int, int]  # chapter ID => address
    end_events: Dict[int, int]  # chapter ID => address
    next_patcher_count: int

    visited_ptrs: Set[int]

    def __init__(self, linker: Linker, rom: ROM):
        self.linker = linker
        self.rom = rom
        self.events = {}
        self.conditions = {}
        self.start_events = {}
        self.end_events = {}
        self.visited_ptrs = set()
        self.next_patcher_count = 0

        for map_ev in rom.load_map_events():
            self.start_events[map_ev.map_id] = map_ev.start_event_addr
            self.end_events[map_ev.map_id] = map_ev.end_event_addr

            self._process_event_pointer(map_ev.pointer_table_addr + 0x48)
            self._process_event_pointer(map_ev.pointer_table_addr + 0x4C)

            for cond in map_ev.iter_event_conditions():
                self._process_event_pointer(cond.condition_addr + 0x04)
                self.conditions[cond.condition_addr] = cond

    def _process_event_pointer(self, ptr_addr: int):
        ptr_addr = ensure_rom_address(ptr_addr)
        if ptr_addr in self.visited_ptrs:
            return
        self.visited_ptrs.add(ptr_addr)

        ev_addr = self.rom.read_int(ptr_addr, 4, signed=False)
        if (ev_addr == 1) or (ev_addr == 0xFFFFFFFF):
            return

        patcher_key = (True, ev_addr)
        if patcher_key not in self.events:
            patcher = EventPatcher(self.rom, self.linker, True, ev_addr)
            self.events[patcher_key] = patcher

            for reloc_offset, _ in patcher.calls():
                self._process_event_pointer(reloc_offset + ev_addr)
        else:
            patcher = self.events[patcher_key]

        self.linker.add_rom_relocation(
            ensure_file_offset(ptr_addr), patcher.symbol, relocation_types.DATA_32
        )

    def get_patcher(self, ev_addr: int) -> EventPatcher:
        return self.events[(True, ensure_rom_address(ev_addr))]

    def new_patcher(self) -> EventPatcher:
        next_id = self.next_patcher_count
        self.next_patcher_count += 1
        patcher = EventPatcher(self.rom, self.linker, False, next_id)
        self.events[(False, next_id)] = patcher
        return patcher

    def get_event_condition(self, cond_addr: int) -> EventCondition:
        return self.conditions[ensure_rom_address(cond_addr)]

    def finalize(self):
        for patcher in self.events.values():
            if patcher.modified:
                patcher.finalize()


class EventPatcher:
    rom: ROM
    linker: Linker
    patcher_key: int
    inst_data: List[Tuple[int, bytes]]
    reloc_calls: Dict[int, str | Symbol]
    reloc_asmcs: Dict[int, str | Symbol]
    reloc_other: Dict[int, Tuple[int, str | Symbol, int]]
    symbol: Symbol
    modified: bool
    cur_inst_id: int
    next_label_id: int

    def __init__(
        self, rom: ROM, linker: Linker, from_rom: bool, patcher_id: int
    ) -> None:
        self.rom = rom
        self.linker = linker
        self.patcher_key = (from_rom, patcher_id)
        self.inst_data = []
        self.reloc_calls = {}
        self.reloc_asmcs = {}
        self.reloc_other = {}
        self.modified = False
        self.cur_inst_id = 0
        self.cur_label_id = 0

        if from_rom:
            ev_addr = patcher_id
            evt = Event(self.rom, ev_addr)
            ev_size = 0
            for _, cmd, inst_data in evt.instructions():
                ev_size += len(inst_data)
                self.inst_data.append((self.cur_inst_id, inst_data))
                self.cur_inst_id += 1
                if cmd == 0x0820:
                    label = int.from_bytes(inst_data[2:4], "little", signed=False)
                    self.cur_label_id = max(label, self.cur_label_id)
            self.cur_label_id += 1

            self.symbol = self.linker.add_rom_symbol(
                self.sym_name,
                ensure_file_offset(ev_addr),
                sym_type=SYM_TYPE_DATA,
                size=ev_size,
                weak_binding=True,
            )
        else:
            self.inst_data.append((0, b"\x20\x01\x00\x00"))
            self.cur_inst_id += 1
            self.cur_label_id += 1
            self.modified = True
            self.symbol = self.linker.add_symbol(
                self.sym_name,
                None,
                None,
                sym_type=SYM_TYPE_DATA,
                size=None,
                weak_binding=True,
            )

    @property
    def sym_name(self) -> str:
        return _event_sym_name(self.patcher_key)

    def instructions(self) -> Iterator[Tuple[int, int, int, bytes]]:
        cur_offset = 0
        for inst_id, data in self.inst_data:
            cmd = int.from_bytes(data[:2], byteorder="little", signed=False)
            yield inst_id, cur_offset, cmd, data
            cur_offset += len(data)

    def calls(self) -> Iterator[Tuple[int, int | str | Symbol]]:
        for inst_id, offset, cmd, data in self.instructions():
            if cmd == 0x0A40:
                try:
                    yield offset + 4, self.reloc_calls[inst_id]
                except KeyError:
                    call_addr = int.from_bytes(data[4:8], "little", signed=False)
                    if (call_addr != 1) and (call_addr != 0xFFFFFFFF):
                        yield offset + 4, call_addr

    def finalize(self):
        data = b"".join(encoded for _, encoded in self.inst_data)
        section = self.linker.add_section(
            self.sym_name, data, section_type=SECTION_TYPE_ROM
        )
        self.symbol = self.linker.add_symbol(
            self.sym_name, 0, section, SYM_TYPE_DATA, size=len(data)
        )

        # Add relocations for event calls
        for offset, call_target in self.calls():
            if isinstance(call_target, int):
                call_target = _event_sym_name(call_target)
            elif isinstance(call_target, EventPatcher):
                call_target = call_target.sym_name

            self.linker.add_relocation(
                section, offset, call_target, relocation_types.DATA_32
            )

        # Add relocations for ASMCs
        for inst_id, offset, _, _ in self.instructions():
            try:
                asmc_target = self.reloc_asmcs[inst_id]
                self.linker.add_relocation(
                    section, offset + 4, asmc_target, relocation_types.OVERWRITE_32
                )
            except KeyError:
                pass

            try:
                reloc_offset, other_target, reloc_type = self.reloc_other[inst_id]
                self.linker.add_relocation(
                    section, offset + reloc_offset, other_target, reloc_type
                )
            except KeyError:
                pass

    def add_instruction(self, cmd: int, *data: bytes, position=-1) -> int:
        # insert before ending instruction
        add_data = cmd.to_bytes(2, "little", signed=False) + b"".join(data)
        cmd_len = (cmd & 0x00F0) >> 3
        if cmd_len != len(add_data):
            raise ValueError(
                f"Event instruction {repr(add_data)} does not have correct length (expected {cmd_len}, got {len(add_data)})"
            )

        inst_id = self.cur_inst_id
        self.inst_data.insert(position, (inst_id, add_data))
        self.cur_inst_id += 1
        self.modified = True
        return inst_id

    def alloc_label(self) -> int:
        label_id = self.cur_label_id
        self.cur_label_id += 1
        return label_id

    def label(self, label_id: int, *, position=-1) -> EventPatcher:
        self.add_instruction(
            0x0820, label_id.to_bytes(2, "little", signed=False), position=position
        )
        return self

    def call(
        self, target: int | str | Symbol | EventPatcher, *, position=-1
    ) -> EventPatcher:
        if isinstance(target, int):
            target = ensure_rom_address(target)
            self.add_instruction(
                0x0A40,
                b"\0\0",
                target.to_bytes(4, "little", signed=False),
                position=position,
            )
        else:
            inst_id = self.add_instruction(
                0x0A40, b"\0\0", b"\0\0\0\0", position=position
            )
            self.reloc_calls[inst_id] = target
        return self

    def asmc(self, target: str | Symbol, *, position=-1) -> EventPatcher:
        inst_id = self.add_instruction(0x0D40, b"\0\0", b"\0\0\0\0", position=position)
        self.reloc_asmcs[inst_id] = target
        return self

    def beq(
        self, slot_a: int, slot_b: int, dest_label: int, *, position=-1
    ) -> EventPatcher:
        slot_a = _ensure_valid_slot(slot_a)
        slot_b = _ensure_valid_slot(slot_b)
        self.add_instruction(
            0x0C40,
            dest_label.to_bytes(2, "little", signed=False),
            slot_a.to_bytes(2, "little", signed=False),
            slot_b.to_bytes(2, "little", signed=False),
            position=position,
        )
        return self

    def set_val(self, slot: int, val: int, *, position=-1) -> EventPatcher:
        slot = _ensure_valid_slot(slot)
        self.add_instruction(
            0x0540,
            slot.to_bytes(2, "little", signed=False),
            val.to_bytes(4, "little", signed=True),
            position=position,
        )
        return self

    def set_val_symbol(
        self,
        slot: int,
        symbol: str | Symbol | EventPatcher,
        reloc_type: int,
        *,
        position=-1,
    ) -> EventPatcher:
        slot = _ensure_valid_slot(slot)
        inst_id = self.add_instruction(
            0x0540,
            slot.to_bytes(2, "little", signed=False),
            b"\0\0\0\0",
            position=position,
        )

        if isinstance(symbol, EventPatcher):
            symbol = symbol.sym_name

        self.reloc_other[inst_id] = (4, symbol, reloc_type)
        return self

    def slot_add(
        self, dest: int, src_a: int, src_b: int, *, position=-1
    ) -> EventPatcher:
        self.add_instruction(
            0x0620,
            _encode_arithmetic_slots(dest, src_a, src_b).to_bytes(
                2, "little", signed=False
            ),
            position=position,
        )
        return self

    def slot_sub(
        self, dest: int, src_a: int, src_b: int, *, position=-1
    ) -> EventPatcher:
        self.add_instruction(
            0x0621,
            _encode_arithmetic_slots(dest, src_a, src_b).to_bytes(
                2, "little", signed=False
            ),
            position=position,
        )
        return self

    def slot_mov(self, dest: int, src: int, *, position=-1) -> EventPatcher:
        return self.slot_add(dest, src, 0)

    def warp_out(self, xy: Optional[Tuple[int, int]], *, position=-1) -> EventPatcher:
        if xy is None:
            # take position from slot 0xB
            self.add_instruction(0x4120, b"\xfe\xff", position=position)
        else:
            x, y = xy
            self.add_instruction(
                0x4120,
                x.to_bytes(1, "little", signed=True),
                y.to_bytes(1, "little", signed=True),
                position=position,
            )
        return self

    def warp_in(self, xy: Optional[Tuple[int, int]], *, position=-1) -> EventPatcher:
        if xy is None:
            self.add_instruction(0x4121, b"\xfe\xff", position=position)
        else:
            x, y = xy
            self.add_instruction(
                0x4121,
                x.to_bytes(1, "little", signed=True),
                y.to_bytes(1, "little", signed=True),
                position=position,
            )
        return self

    def warp_end(self, *, position=-1) -> EventPatcher:
        self.add_instruction(0x412F, b"\0\0", position=position)
        return self

    def evbit_modify(self, mode: int, *, position=-1) -> EventPatcher:
        self.add_instruction(
            0x1020, mode.to_bytes(2, "little", signed=False), position=position
        )
        return self

    def set_evbit(self, bit: int, val: bool, *, position=-1) -> EventPatcher:
        if val:
            self.add_instruction(
                0x0228, bit.to_bytes(2, "little", signed=False), position=position
            )
        else:
            self.add_instruction(
                0x0220, bit.to_bytes(2, "little", signed=False), position=position
            )
        return self
