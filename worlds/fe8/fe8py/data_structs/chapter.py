from __future__ import annotations

import random
from typing import TYPE_CHECKING, Dict, Iterator, List, Optional, Set, Tuple, Union

from ..linker import relocation_types
from ..rom_file import ensure_file_offset, ensure_rom_address
from ..rom_struct import (
    ArrayField,
    Field,
    PointerField,
    RomStruct,
    StructAddress,
    StructID,
    rom_struct,
)
from .event import Chest, Event, GivenItem, Shop, UnitDefinition

if TYPE_CHECKING:
    from ..linker import Linker, Symbol
    from ..rom import ROM


@rom_struct
class AfterEventCondition(RomStruct):
    rom: ROM
    condition_addr: int = StructAddress()

    complete_flag: int = Field.u16(0x02)
    event_addr: int = PointerField(0x04)
    trigger_flag: int = Field.u16(0x08)

    def __post_save__(self):
        self.rom.write_int(0x0001, self.condition_addr, 2, signed=False)

    def relocate_event(self, linker: Linker, symbol: Union[str, Symbol]):
        linker.add_rom_relocation(
            ensure_file_offset(self.condition_addr + 0x04),
            symbol,
            relocation_types.DATA_32,
        )


@rom_struct
class TurnEventCondition(RomStruct):
    rom: ROM
    condition_addr: int = StructAddress()

    complete_flag: int = Field.u16(0x02)
    event_addr: int = PointerField(0x04)
    start_turn: int = Field.u8(0x08)
    end_turn: int = Field.u8(0x09)
    phase: int = Field.u8(0x0A)

    def __post_save__(self):
        self.rom.write_int(0x0002, self.condition_addr, 2, signed=False)

    @property
    def is_player_phase(self) -> bool:
        return (self.phase & 0xF0) == 0x00

    @property
    def is_enemy_phase(self) -> bool:
        return (self.phase & 0xF0) == 0x80

    @property
    def is_npc_phase(self) -> bool:
        return (self.phase & 0xF0) == 0x40

    def relocate_event(self, linker: Linker, symbol: Union[str, Symbol]):
        linker.add_rom_relocation(
            ensure_file_offset(self.condition_addr + 0x04),
            symbol,
            relocation_types.DATA_32,
        )


@rom_struct
class TalkEventCondition(RomStruct):
    rom: ROM
    condition_addr: int = StructAddress()

    complete_flag: int = Field.u16(0x02)
    event_addr: int = PointerField(0x04)
    init_character: int = Field.u8(
        0x08
    )  # Character that does the "Talk" command to start the event
    target_character: int = Field.u8(0x09)
    extra_condition: int = Field.u32(0x0C)

    def __post_save__(self):
        self.rom.write_int(0x0003, self.condition_addr, 2, signed=False)

    @property
    def trigger_flag(self) -> Optional[int]:
        if (self.extra_condition & 0x000000FF) == 0x03:
            return (self.extra_condition & 0x00FFFF00) >> 8
        else:
            return None

    def with_trigger_flag(self, flag: Optional[int]) -> TalkEventCondition:
        if flag is not None:
            return self.evolve(extra_condition=((flag & 0xFFFF) << 8) | 0x03)
        else:
            return self.evolve(extra_condition=0)

    def relocate_event(self, linker: Linker, symbol: Union[str, Symbol]):
        linker.add_rom_relocation(
            ensure_file_offset(self.condition_addr + 0x04),
            symbol,
            relocation_types.DATA_32,
        )


@rom_struct
class LocationEventCondition(RomStruct):
    rom: ROM
    condition_addr: int = StructAddress()

    complete_flag: int = Field.u16(0x02)
    data_addr: int = Field.u32(0x04)  # Might be 1, so not a PointerField
    position: Tuple[int, int] = ArrayField.u8(0x08, 2)
    location_type: int = Field.u16(
        0x0A
    )  # 0x11 = seize point, 0x10 = home, 0x20 = thief target, 0x14 = random chest

    def __post_save__(self):
        self.rom.write_int(0x0005, self.condition_addr, 2, signed=False)

    @property
    def event_addr(self) -> Optional[int]:
        if (self.data_addr != 1) and (self.data_addr != 0xFFFFFFFF):
            return ensure_rom_address(self.data_addr)
        else:
            return None

    def with_event_addr(self, event_addr: Optional[int]) -> LocationEventCondition:
        if event_addr is not None:
            return self.evolve(data_addr=event_addr)
        else:
            return self.evolve(data_addr=1)

    def relocate_event(self, linker: Linker, symbol: Union[str, Symbol]):
        linker.add_rom_relocation(
            ensure_file_offset(self.condition_addr + 0x04),
            symbol,
            relocation_types.DATA_32,
        )


@rom_struct
class VillageEventCondition(RomStruct):
    rom: ROM
    condition_addr: int = StructAddress()

    complete_flag: int = Field.u16(0x02)
    data_addr: int = Field.u32(0x04)
    position: Tuple[int, int] = ArrayField.u8(0x08, 2)
    location_type: int = Field.u16(0x0A)  # 0x10 = village, 0x20 = thief target

    def __post_save__(self):
        self.rom.write_int(0x0006, self.condition_addr, 2, signed=False)

    @property
    def event_addr(self) -> Optional[int]:
        if (self.data_addr != 1) and (self.data_addr != 0xFFFFFFFF):
            return ensure_rom_address(self.data_addr)
        else:
            return None

    def with_event_addr(self, event_addr: Optional[int]) -> VillageEventCondition:
        if event_addr is not None:
            return self.evolve(data_addr=event_addr)
        else:
            return self.evolve(data_addr=1)

    def relocate_event(self, linker: Linker, symbol: Union[str, Symbol]):
        linker.add_rom_relocation(
            ensure_file_offset(self.condition_addr + 0x04),
            symbol,
            relocation_types.DATA_32,
        )


EventCondition = Union[
    AfterEventCondition,
    TurnEventCondition,
    TalkEventCondition,
    LocationEventCondition,
    VillageEventCondition,
]


class MapEvents:
    rom: ROM
    map_id: int
    index: int
    map_name: str

    pointer_table_addr: int
    start_event_addr: int
    end_event_addr: int

    unit_definitions: List[UnitDefinition]
    given_items: List[GivenItem]
    chests: List[Chest]
    shops: List[Shop]

    flag_events: List[AfterEventCondition]
    turn_events: List[TurnEventCondition]
    talk_events: List[TalkEventCondition]
    location_events: List[Union[LocationEventCondition, VillageEventCondition]]

    def __init__(
        self,
        rom: ROM,
        map_id: int,
        index: int,
        map_name: str,
        extra_addrs: Optional[List[int]] = None,
    ):
        self.rom = rom
        self.map_id = map_id
        self.index = index
        self.map_name = map_name

        self.unit_definitions = []
        self.given_items = []
        self.chests = []
        self.shops = []

        self.pointer_table_addr = self.rom.read_addr(0x088B363C + (self.index * 4))
        chest_addrs = set()
        shop_addrs = set()
        unit_def_addrs = {}
        item_addrs = set()

        self.flag_events = []
        self.turn_events = []
        self.talk_events = []
        self.location_events = []

        for offset in (0, 0x04, 0x08, 0x0C):
            cur_addr = self.rom.read_addr(self.pointer_table_addr + offset)
            while True:
                cmd = self.rom.read_int(cur_addr, 2)
                if cmd == 0:
                    break
                elif cmd == 0x0001:
                    self.flag_events.append(
                        AfterEventCondition.load(self.rom, cur_addr)
                    )
                elif cmd == 0x0002:
                    self.turn_events.append(TurnEventCondition.load(self.rom, cur_addr))
                elif cmd == 0x0003:
                    self.talk_events.append(TalkEventCondition.load(self.rom, cur_addr))
                elif cmd == 0x0005:
                    if cmd == 0x0005:
                        loca_cmd = self.rom.read_int(cur_addr + 0x0A, 2)
                        if loca_cmd == 0x14:
                            continue  # this is actually a CHESRANDOM command
                    self.location_events.append(
                        LocationEventCondition.load(self.rom, cur_addr)
                    )
                elif cmd == 0x0006:
                    self.location_events.append(
                        VillageEventCondition.load(self.rom, cur_addr)
                    )
                elif cmd == 0x0007:  # CHES
                    chest_addrs.add(cur_addr)
                elif cmd == 0x000A:  # SHOP
                    shop_addrs.add(cur_addr)

                if cmd == 0x0003:
                    cur_addr += 16
                else:
                    cur_addr += 12

        event_addrs = set()
        for cond in self.iter_event_conditions():
            if (
                (cond.event_addr is not None)
                and (cond.event_addr != 1)
                and (cond.event_addr != 0xFFFFFFFF)
            ):
                event_addrs.add(cond.event_addr)

        self.chests = [Chest.load(rom, addr) for addr in chest_addrs]
        self.shops = [Shop(rom, addr + 4) for addr in shop_addrs]

        self.start_event_addr = self.rom.read_int(self.pointer_table_addr + 0x48, 4)
        self.end_event_addr = self.rom.read_int(self.pointer_table_addr + 0x4C, 4)

        event_addrs.add(self.start_event_addr)
        event_addrs.add(self.end_event_addr)
        if extra_addrs is not None:
            event_addrs.update(extra_addrs)

        for event_addr in event_addrs:
            event = Event(rom, event_addr)
            unit_def_addrs.update(event.unit_definitions)
            item_addrs.update(event.item_addrs)

        unit_def_addrs[self.rom.read_addr(self.pointer_table_addr + 0x28)] = None
        unit_def_addrs[self.rom.read_addr(self.pointer_table_addr + 0x2C)] = None
        self.given_items = [GivenItem.load(rom, addr) for addr in item_addrs]

        loaded_addrs = set()
        for def_addr, load_type in unit_def_addrs.items():
            while True:
                if def_addr not in loaded_addrs:
                    def_char_id = self.rom.read_int(def_addr, 1)
                    if def_char_id != 0:
                        self.unit_definitions.append(
                            UnitDefinition(rom, def_addr, load_type)
                        )
                    else:
                        break
                def_addr += 0x14

    def iter_event_conditions(self) -> Iterator[EventCondition]:
        for ev_list in (
            self.flag_events,
            self.turn_events,
            self.talk_events,
            self.location_events,
        ):
            yield from ev_list

    def load_start_event(self) -> Event:
        return Event(self.rom, self.start_event_addr)

    def load_end_event(self) -> Event:
        return Event(self.rom, self.end_event_addr)


class ChapterMetadata:
    rom: ROM
    index: int
    title_text_id: int
    event_data_id: int
    world_map_event_data_id: int

    def __init__(self, rom: ROM, index: int):
        addr = 0x088B0890 + (index * 0x94)
        self.rom = rom
        self.index = index
        self.title_text_id = self.rom.read_int(addr + 0x70, 2)
        self.event_data_id = self.rom.read_int(addr + 0x74, 1)
        self.world_map_event_data_id = self.rom.read_int(addr + 0x75, 1)

        assert (self.world_map_event_data_id > 0) and (
            self.world_map_event_data_id < 59
        )

    @property
    def title(self) -> str:
        return str(self.rom.get_message(self.title_text_id))

    @property
    def is_split_chapter(self) -> bool:
        return (
            ((self.index >= 0x0A) and (self.index < 0x24))
            or (self.index == 0x3D)
            or (self.index == 0x3E)
        )

    @property
    def alternate_chapter_index(self) -> Optional[int]:
        if self.index >= 0x0A and self.index < 0x17:  # Erika route
            return self.index + 13
        elif self.index >= 0x17 and self.index < 0x24:  # Ephraim route
            return self.index - 13
        elif self.index == 0x3D:  # Creeping Darkness (Erika)
            return 0x3E
        elif self.index == 0x3E:  # Phantom Ship (Ephraim)
            return 0x3D
        return None

    @classmethod
    def load_all(cls, rom: ROM) -> Iterator[ChapterMetadata]:
        for i in range(0, 0x0A):
            yield cls(rom, i)

        for i in range(0x0A, 0x0C):
            yield cls(rom, i)
            yield cls(rom, i + 13)

        yield cls(rom, 0x3D)
        yield cls(rom, 0x3E)

        for i in range(0x0C, 0x17):
            yield cls(rom, i)
            yield cls(rom, i + 13)

        yield cls(rom, 0x38)  # Castle Frelia

        # for i in range(0, 0x24):
        #     yield cls(rom, i)
        # yield cls(rom, 0x3D)
        # yield cls(rom, 0x3E)

    def load_chapter_events(self) -> MapEvents:
        wm_event1 = self.rom.read_addr(0x088B39EC + (self.world_map_event_data_id * 4))
        wm_event2 = self.rom.read_addr(0x088B3AD8 + (self.world_map_event_data_id * 4))
        return MapEvents(
            self.rom,
            self.index,
            self.event_data_id,
            str(self),
            [wm_event1, wm_event2],
        )

    def __str__(self) -> str:
        return "Chapter {:02X} : {}".format(self.index, self.title)


@rom_struct
class WorldMapNode(RomStruct):
    rom: ROM
    node_id: int = StructID(
        index_size=1, base_address=0x082060B0, struct_size=0x20, index_adjustment=0
    )

    placementFlag: int = Field.u8(0x00)
    skirmishType: int = Field.u8(0x01)
    preClearIcon: int = Field.u8(0x02)
    postClearIcon: int = Field.u8(0x03)
    eirikaChapterId: int = Field.u8(0x04)
    ephraimChapterId: int = Field.u8(0x05)
    eventConditionFlag: int = Field.u16(0x06)

    nextWMNode_Erika1: int = Field.u8(0x08)
    nextWMNode_Ephraim1: int = Field.u8(0x09)
    nextWMNode_Erika2: int = Field.u8(0x0A)
    nextWMNode_Ephraim2: int = Field.u8(0x0B)

    armoryData: int = PointerField(0x0C)
    vendorData: int = PointerField(0x10)
    secretShopData: int = PointerField(0x14)

    posX: int = Field.u16(0x18)
    posY: int = Field.u16(0x1A)

    nameTextId: int = Field.u16(0x1C)

    @property
    def name(self) -> str:
        self.rom.get_message(self.nameTextId)

    @classmethod
    def load_all(cls, rom: ROM) -> Iterator[WorldMapNode]:
        for i in range(29):
            yield cls.load(rom, i)

    def load_armory(self) -> Optional[Shop]:
        ret = Shop(self.rom, (0x082060B0 + (0x20 * self.node_id)) + 0x0C)
        if len(ret.item_ids) == 0:
            return None
        return ret

    def load_vendor(self) -> Optional[Shop]:
        ret = Shop(self.rom, (0x082060B0 + (0x20 * self.node_id)) + 0x10)
        if len(ret.item_ids) == 0:
            return None
        return ret

    def load_secret_shop(self) -> Optional[Shop]:
        ret = Shop(self.rom, (0x082060B0 + (0x20 * self.node_id)) + 0x14)
        if len(ret.item_ids) == 0:
            return None
        return ret

    def __str__(self) -> str:
        return "{} (Chapter {:02x}/{:02x})".format(
            self.name, self.eirikaChapterId, self.ephraimChapterId
        )
