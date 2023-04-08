from __future__ import annotations

import random
from typing import TYPE_CHECKING, Dict, Iterator, List, Optional, Set, Tuple, Union

from ..rom_struct import Field, RomStruct, StructAddress, rom_struct

if TYPE_CHECKING:
    from ..rom import ROM
    from ..rom_file import ROMFile
    from .character_data import CharacterData
    from .class_data import ClassData
    from .item_data import ItemData


class UnitDefinition:
    rom: ROM
    addr: int

    character_id: int
    class_id: int
    leader_id: int

    props_1: int
    props_2: int
    props_3: int

    items: Tuple[Optional[int], Optional[int], Optional[int], Optional[int]]

    def __init__(self, rom: ROM, addr: int, load_type: Optional[int]):
        self.addr = addr
        self.rom = rom
        self.load_type = load_type

        self.character_id = self.rom.read_int(addr, 1)
        self.class_id = self.rom.read_int(addr + 0x01, 1)
        self.leader_id = self.rom.read_int(addr + 0x02, 1)
        self.props_1 = self.rom.read_int(addr + 0x03, 1)
        self.props_2 = self.rom.read_int(addr + 0x04, 2)
        self.props_3 = self.rom.read_int(addr + 0x06, 2)
        self.items = []
        for i in range(4):
            item_id = self.rom.read_int(addr + 0x0C + i, 1)
            if item_id == 0:
                self.items.append(None)
            else:
                self.items.append(item_id)
        self.items = tuple(self.items)

    def save(self):
        self.rom.write_int(self.character_id, self.addr, 1)
        self.rom.write_int(self.class_id, self.addr + 0x01, 1)
        self.rom.write_int(self.leader_id, self.addr + 0x02, 1)
        self.rom.write_int(self.props_1, self.addr + 0x03, 1)
        self.rom.write_int(self.props_2, self.addr + 0x04, 2)
        self.rom.write_int(self.props_3, self.addr + 0x06, 2)
        for i, item_id in enumerate(self.items):
            if item_id is not None:
                self.rom.write_int(item_id, self.addr + 0x0C + i, 1)
            else:
                self.rom.write_int(0, self.addr + 0x0C + i, 1)

    @property
    def character(self) -> CharacterData:
        return self.rom.get_character(self.character_id)

    @character.setter
    def character(self, value: Union[CharacterData, int]):
        try:
            self.character_id = value.character_id
        except AttributeError:
            self.character_id = value

    @property
    def unit_class(self) -> ClassData:
        return self.rom.get_class(self.class_id)

    @unit_class.setter
    def unit_class(self, value: Union[ClassData, int]):
        try:
            self.class_id = value.class_id
        except AttributeError:
            self.class_id = value

    @property
    def is_enemy(self) -> bool:
        return ((self.props_1 >> 1) & 0x03) == 2

    @property
    def is_npc(self) -> bool:
        return ((self.props_1 >> 1) & 0x03) == 1

    @property
    def is_player(self) -> bool:
        return ((self.props_1 >> 1) & 0x03) == 0

    @property
    def level(self) -> int:
        return (self.props_1 >> 3) & 0x1F

    def set_level(self, level: int):
        self.props_1 = (self.props_1 & 0x07) | ((level << 3) & 0xF8)

    @property
    def is_initial_load(self) -> bool:
        return self.load_type == 0x2C40


@rom_struct
class GivenItem(RomStruct):
    rom: ROM
    item_addr: int = StructAddress()
    _item_id: int = Field.u32(0x00)

    @property
    def item_id(self) -> int:
        return self._item_id & 0xFF

    @property
    def item(self) -> ItemData:
        return self.rom.get_item(self._item_id & 0xFF)

    def with_item(self, value: Union[ItemData, int]) -> GivenItem:
        try:
            new_item_id = value.item_id
        except AttributeError:
            new_item_id = value

        return self.evolve(_item_id=new_item_id & 0xFF)


@rom_struct
class Chest(RomStruct):
    rom: ROM
    event_addr: int = StructAddress()
    contents: int = Field.u32(0x04)

    @property
    def item_id(self) -> Optional[int]:
        if self.contents & 0xFFFFFF00 != 0:
            return None
        else:
            return self.contents & 0xFF

    @property
    def money(self) -> Optional[int]:
        if self.contents & 0x000000FF != 0:
            return None
        else:
            return (self.contents >> 16) & 0x0000FFFF

    @property
    def item(self) -> Optional[ItemData]:
        if self.item_id is not None:
            return self.rom.get_item(self.item_id)

    def with_item(self, value: Union[ItemData, int]) -> Chest:
        try:
            new_item_id = value.item_id
        except AttributeError:
            new_item_id = value

        return self.evolve(contents=new_item_id & 0xFF)

    def with_money(self, value: int) -> Chest:
        return self.evolve(contents=(value & 0xFFFF) << 16)


class Shop:
    rom: ROM
    item_list_ptr: int
    item_ids: List[int]

    def __init__(self, rom: ROM, item_list_ptr: int):
        self.rom = rom
        self.item_list_ptr = item_list_ptr
        self.item_ids = []

        cur_addr = self.rom.read_addr(self.item_list_ptr)
        while True:
            item = self.rom.read_int(cur_addr, 2) & 0xFF
            if item != 0:
                self.item_ids.append(item)
                cur_addr += 2
            else:
                break

    def save(self):
        cur_addr = self.rom.read_addr(self.item_list_ptr)
        for i, item in enumerate(self.item_ids):
            self.rom.write_int(item & 0xFF, cur_addr + (i * 2), 2)
        self.rom.write_int(0, cur_addr + (len(self.item_ids) * 2), 2)

    def iter_items(self) -> Iterator[ItemData]:
        return map(self.rom.get_item, self.item_ids)

    def set_item(self, index: int, value: Union[ItemData, int]):
        try:
            self.item_ids[index] = value.item_id
        except AttributeError:
            self.item_ids[index] = value


class Event:
    rom: ROM
    addr: int
    unit_definitions: Dict[int, int]
    item_addrs: Set[int]

    def __init__(self, rom: ROM, addr: int):
        self.rom = rom
        self.addr = addr
        self.unit_definitions = {}
        self.item_addrs = set()
        self._get_units_and_items(addr)

    @staticmethod
    def _iter_instructions(
        rom: ROMFile, start_addr: int
    ) -> Iterator[Tuple[int, int, bytes]]:
        cur_addr = start_addr
        while True:
            cmd = rom.read_int(cur_addr, 2)
            cmd_len = (cmd & 0x00F0) >> 3

            cmd_data = rom.read_bytes(cur_addr, cmd_len)
            yield (cur_addr, cmd, cmd_data)
            cur_addr += cmd_len

            if cmd == 0x0120 or cmd == 0x0121:
                return

    def instructions(self) -> Iterator[Tuple[int, int, bytes]]:
        yield from Event._iter_instructions(self.rom.file, self.addr)

    @staticmethod
    def _asmc_sequence(paramA: int, paramB: int) -> bytearray:
        asmc_sequence = bytearray(b"\x40\x05\x01\x00")
        asmc_sequence.extend(paramA.to_bytes(4, "little", signed=True))
        asmc_sequence.extend(b"\x40\x05\x02\x00")
        asmc_sequence.extend(paramB.to_bytes(4, "little", signed=True))
        asmc_sequence.extend(b"\x40\x0D\x00\x00\x00\x00\x00\x00")
        return asmc_sequence

    def inject_starting_asmc(self, paramA: int, paramB: int) -> Tuple[bytearray, int]:
        # Returns bytes for new event data, followed by offset to patch to set ASMC target
        ret = Event._asmc_sequence(paramA, paramB)
        inject_offset = len(ret) - 4
        for (_, _, data) in self.instructions():
            ret.extend(data)
        return ret, inject_offset

    def _get_units_and_items(
        self,
        start_addr: int,
        slots: Optional[List[int]] = None,
        slot_setval_addrs: Optional[List[int]] = None,
    ):
        if slots is None:
            slots = [0] * 14
            slot_setval_addrs = [None] * 14

        for (cur_addr, cmd, data) in Event._iter_instructions(
            self.rom.file, start_addr
        ):
            if cmd == 0x2C40:  # LOAD1
                op_addr = int.from_bytes(data[4:8], "little")
                if op_addr != 0xFFFFFFFF:
                    self.unit_definitions[op_addr] = cmd
                else:
                    self.unit_definitions[slots[2]] = cmd
            elif cmd == 0x2C41 or cmd == 0x2C42:  # LOAD2, LOAD3
                op_addr = int.from_bytes(data[4:8], "little")
                if op_addr != 0xFFFFFFFF:
                    self.unit_definitions[op_addr] = cmd
            elif cmd == 0x3720:  # GIVEITEMTO
                if slot_setval_addrs[0x03] is not None:
                    self.item_addrs.add(slot_setval_addrs[0x03])
            elif cmd == 0x0540:  # SETVAL
                slot = int.from_bytes(data[2:4], "little")
                val = int.from_bytes(data[4:8], "little")
                if slot > 0:
                    slots[slot] = val
                    slot_setval_addrs[slot] = cur_addr + 4
            elif cmd == 0x0A40:  # CALL
                call_addr = int.from_bytes(data[4:8], "little")
                if call_addr != 0xFFFFFFFF:
                    self._get_units_and_items(call_addr, slots, slot_setval_addrs)
            elif (cmd >= 0x0620) and (cmd <= 0x0629):  # Slot arithmetic/bit ops
                op_a = int.from_bytes(data[2:3], "little")
                op_b = int.from_bytes(data[3:4], "little")
                src_x = op_b & 0x0F
                src_y = (op_a >> 4) & 0x0F
                dest = op_a & 0x0F

                if cmd == 0x0620:
                    slots[dest] = slots[src_x] + slots[src_y]
                elif cmd == 0x0621:
                    slots[dest] = slots[src_y] - slots[src_x]
                elif cmd == 0x0622:
                    slots[dest] = slots[src_x] * slots[src_y]
                elif cmd == 0x0623:
                    slots[dest] = slots[src_y] // slots[src_x]
                elif cmd == 0x0624:
                    slots[dest] = slots[src_y] % slots[src_x]
                elif cmd == 0x0625:
                    slots[dest] = slots[src_x] & slots[src_y]
                elif cmd == 0x0626:
                    slots[dest] = slots[src_x] | slots[src_y]
                elif cmd == 0x0627:
                    slots[dest] = slots[src_x] ^ slots[src_y]
                elif cmd == 0x0628:
                    slots[dest] = slots[src_y] << slots[src_x]
                elif cmd == 0x0629:
                    slots[dest] = (slots[src_y] >> slots[src_x]) & 0xFFFFFFFF
                slots[0] = 0
