from __future__ import annotations

import bisect
import json
import os.path as osp
import struct
import sys
import time
from typing import Dict, List, Optional, Tuple, Union

from attrs import asdict, define, field
from fe8py.linker.relocation_types import RELOCATION_TYPES
from progress_line import ProgressLine

SYM_TYPE_UNKNOWN = 0
SYM_TYPE_DATA = 1
SYM_TYPE_ARM = 2
SYM_TYPE_THUMB = 3

SECTION_TYPE_ROM = 0
SECTION_TYPE_WRAM = 1


@define
class StoredSymbol:
    name: str
    offset: int
    size: int
    type: str  # unknown / data / arm / thumb
    space: str  # rom / wram

    @property
    def address(self) -> int:
        if self.space == "rom":
            return self.offset + 0x08000000
        elif self.space == "wram":
            return self.offset + 0x02000000


@define
class StoredRelocation:
    offset: int
    symbol_name: str
    type: int
    addend: int
    original_field: int
    space: str


GET_SYMS = [
    "gBattleActor",
    "gBattleTarget",
    "gRAMChapterData",
    "GetBattleUnitExpGain",
    "GetBattleUnitStaffExp",
    "CheckBattleUnitLevelUp",
    "MenuAlwaysNotShown",
    "gCharacterData",
    "gClassData",
    "gItemData",
    # "Event25_",
    # "Event2A_MoveToChapter",
    "gEventSlots",
    # "ExecMainUpdate",
    # "gMainCallback",
    "gProc_BMapMain",
    "sProcArray",
    "sProcAllocList",
    "sProcAllocListHead",
    "Proc_Find",
    "Proc_StartBlocking",
    "Proc_Goto",
    "EventEngineExists",
    "PlayerPhase_MainIdle",
    "CallEvent",
    "StartPlayerPhaseSideWindows",
    "EndPlayerPhaseSideWindows",
    "RefreshEntityBmMaps",
    "RenderBmMap",
    "RefreshUnitSprites",
    "ResetUnitSpriteHover",
    "StartMapSongBgm",
    "gEventCallQueue",
    "EventEngine_Create",
    "gUnknown_08A3EE74",  # world map rendering proc
    "Proc_Find",
    "GetUnitFromCharId",
    "gActiveUnit",
    "gBmMapUnit",
    "gBmMapMovement",
    "gBmMapTerrain",
    "gBmMapHidden",
    "GetUnitMovementCost",
    "gBmMapSize",
    # "EnqueueEventCall",
    # "WriteAndVerifySramFast",
    # "ReadSramFast",
]

GET_RELOCS = [
    "gMsgHuffmanTable",
    "gMsgStringTable",
    "gUnknown_089ECD4C",  # death quote table
    # "Event25_",
    # "Event2A_MoveToChapter",
]

GET_SHIM_RELOCS = [
    "UnitKill",
    "BattleApplyExpGains",
    "BattleApplyItemExpGains",
    "BattleApplyMiscActionExpGains",
    "TickActiveFactionTurn",
    "sub_80A9250",
    "SaveGame",
    "CopyGameSave",
    "LoadGame",
    # "SaveSuspendedGame",
    # "LoadSuspendedGame",
    "InitRN",
    "NextRN",
    "LoadRNState",
    "StoreRNState",
    "RunPotentialWaitEvents",
    "sub_80B93E0",  # seems to be involved in WM input handling
]

OVERRIDE_SYMS = [
    StoredSymbol("gUnitLookup", 0x0059A5D0, 256 * 4, SYM_TYPE_DATA, "rom"),
    StoredSymbol("gCharacterData", 0x00803D64, None, SYM_TYPE_DATA, "rom"),
    StoredSymbol("gClassData", 0x00807164, None, SYM_TYPE_DATA, "rom"),
    StoredSymbol("gItemData", 0x00809B10, 7416, SYM_TYPE_DATA, "rom"),
    # Dumb hack: these are IWRAM symbols
    StoredSymbol("ReadSramFast", 0x010067A0, 4, SYM_TYPE_DATA, "wram"),
    StoredSymbol("gEventCallQueue", 0x01000438, 4 * 0x10, SYM_TYPE_DATA, "wram"),
    StoredSymbol("gEventSlots", 0x010004B8, 4 * 0x0E, SYM_TYPE_DATA, "wram"),
    StoredSymbol("gActiveUnit", 0x01004E50, 4, SYM_TYPE_DATA, "wram"),
]
EXTRA_RELOCS = [
    StoredRelocation(0x0002C5EA, "GetBattleUnitStaffExp", 10, 0, -2, "rom"),
    StoredRelocation(0x000A51F4, "ReadSramFast", 2, 0, 0, "rom"),
    StoredRelocation(0x000A5D5C, "ReadSramFast", 2, 0, 0, "rom"),
]


class ELFSectionHeader:
    file: ELF
    name_index: int
    type: int
    flags: int
    address: int
    offset: int
    size: int
    link: int
    info: int
    addr_align: int
    ent_size: int

    def __init__(self, file: ELF, offset: int) -> None:
        self.file = file
        self.name_index = file.read_word(offset)
        self.type = file.read_word(offset + 4)
        self.flags = file.read_word(offset + 8)
        self.address = file.read_word(offset + 12)
        self.offset = file.read_offset(offset + 16)
        self.size = file.read_word(offset + 20)
        self.link = file.read_word(offset + 24)
        self.info = file.read_word(offset + 28)
        self.addr_align = file.read_word(offset + 32)
        self.ent_size = file.read_word(offset + 36)

    @property
    def name(self) -> str:
        end_idx = self.file.section_name_strings.index(b"\0", self.name_index)
        return self.file.section_name_strings[self.name_index : end_idx].decode("utf-8")

    @property
    def is_progbits(self) -> bool:
        return self.type == 1

    @property
    def is_symbol_table(self) -> bool:
        return self.type == 2

    @property
    def is_string_table(self) -> bool:
        return self.type == 3

    @property
    def is_rela(self) -> bool:
        return self.type == 4

    @property
    def is_rel(self) -> bool:
        return self.type == 9

    @property
    def is_nobits(self) -> bool:
        return self.type == 8

    @property
    def data(self) -> bytes:
        if self.is_nobits:
            return bytes()
        else:
            return self.file.data[self.offset : self.offset + self.size]

    def read_half(self, offset: int) -> int:
        return self.file.read_half(self.offset + offset)

    def read_word(self, offset: int) -> int:
        return self.file.read_word(self.offset + offset)

    def read_sword(self, offset: int) -> int:
        return self.file.read_sword(self.offset + offset)

    def read_addr(self, offset: int) -> int:
        return self.file.read_addr(self.offset + offset)

    def read_offset(self, offset: int) -> int:
        return self.file.read_offset(self.offset + offset)


class ELF:
    name: str
    data: bytes
    byte_order: str
    section_headers: List[ELFSectionHeader]
    section_name_strings: bytes
    strings: bytes

    def __init__(self, name: str, data: bytes):
        self.name = name
        self.data = data

        if data[:4] != b"\x7fELF":
            raise ValueError("Invalid ELF header")

        if data[4] != 1:
            raise ValueError("Invalid ELF class " + str(data[4]))

        if data[5] == 1:
            self.byte_order = "little"
        elif data[5] == 2:
            self.byte_order = "big"
        else:
            raise ValueError("Invalid ELF data encoding " + str(data[5]))

        if data[6] != 1:
            raise ValueError("Invalid ELF version " + str(data[6]))

        if self.read_half(18) != 40:  # e_machine, should be 40 for ARM/Thumb
            raise ValueError("Invalid ELF machine type " + str(self.read_half(18)))

        section_header_offset = self.read_offset(32)
        if section_header_offset == 0:
            raise ValueError("ELF file has no section headers?")

        section_entry_size = self.read_half(46)
        section_entry_num = self.read_half(48)
        section_name_table_idx = self.read_half(50)

        self.section_headers = []
        for idx in range(section_entry_num):
            offset = section_header_offset + (idx * section_entry_size)
            self.section_headers.append(ELFSectionHeader(self, offset))
        self.section_name_strings = (
            self.section_headers[section_name_table_idx].data + b"\0"
        )

        self.strings = None
        for i, section in enumerate(self.section_headers):
            if section.is_string_table and i != section_name_table_idx:
                if self.strings is not None:
                    raise ValueError("ELF file has multiple string tables?")
                self.strings = section.data

    @classmethod
    def load_file(cls, fname: str) -> ELF:
        with open(fname, "rb") as f:
            data = f.read()
        return cls(osp.split(fname)[1], data)

    def get_string(self, index: int) -> str:
        end_idx = self.strings.index(b"\0", index)
        return self.strings[index:end_idx].decode("utf-8").strip()

    def read_half(self, offset: int) -> int:
        return int.from_bytes(self.data[offset : offset + 2], self.byte_order)

    def read_word(self, offset: int) -> int:
        return int.from_bytes(self.data[offset : offset + 4], self.byte_order)

    def read_sword(self, offset: int) -> int:
        return int.from_bytes(
            self.data[offset : offset + 4], self.byte_order, signed=True
        )

    def read_addr(self, offset: int) -> int:
        return int.from_bytes(self.data[offset : offset + 4], self.byte_order)

    def read_offset(self, offset: int) -> int:
        return int.from_bytes(self.data[offset : offset + 4], self.byte_order)


def read_data(file: ELF):
    # Load PROGBITS (code/data) and NOBITS (BSS?) sections:
    rom_sh_idx = None
    ewram_sh_idx = None

    progress = ProgressLine()

    for sh_idx, sh_header in enumerate(file.section_headers):
        if sh_header.name == "ROM":
            progress.log("i", "Found ROM section at index {}", sh_idx)
            rom_sh_idx = sh_idx
            rom_data = sh_header.data
        elif sh_header.name == "EWRAM":
            progress.log("i", "Found EWRAM section at index {}", sh_idx)
            ewram_sh_idx = sh_idx

    # Load symbol table:
    symbols: Dict[int, StoredSymbol] = {}
    for sh_idx, sh_header in enumerate(file.section_headers):
        if not sh_header.is_symbol_table:
            continue

        section_type_ranges: Dict[int, List[Tuple[int, int, int]]] = {}
        n_syms = len(sh_header.data) // sh_header.ent_size
        sym_data = {}

        for i, unpacked in enumerate(struct.iter_unpack("<IIIBxH", sh_header.data)):
            name_idx, value, size, info, section_idx = unpacked
            if section_idx == rom_sh_idx:
                sym_space = "rom"
                sym_base = 0x08000000
            elif section_idx == ewram_sh_idx:
                sym_space = "wram"
                sym_base = 0x02000000
            else:
                continue

            if size == 0:
                size = None

            sym_binding = (info >> 4) & 0x0F
            sym_type = info & 0x0F
            section_ranges = section_type_ranges.setdefault(section_idx, [])
            name = file.get_string(name_idx)

            if name == "$t":
                section_ranges.append((value, SYM_TYPE_THUMB))
            elif name == "$a":
                section_ranges.append((value, SYM_TYPE_ARM))
            elif name == "$d":
                section_ranges.append((value, SYM_TYPE_DATA))
            elif section_idx not in (0xFFF1, 0xFFF2, 0):
                override_type = None
                if sym_type == 2:
                    if (value & 1) != 0:
                        override_type = SYM_TYPE_THUMB
                    else:
                        override_type = SYM_TYPE_ARM
                    value &= ~1
                sym_data[i] = (
                    section_idx,
                    name,
                    value,
                    sym_space,
                    sym_base,
                    override_type,
                    size,
                )

            progress.update(
                "Processed {}/{} symbols ({:.0%})", i + 1, n_syms, (i + 1) / n_syms
            )

        progress.finish("Finished processing {} symbols", n_syms)

        sec_keys = list(section_type_ranges.keys())
        for k in sec_keys:
            ranges = []
            range_data = sorted(section_type_ranges[k], key=lambda pair: pair[0])
            prev_addr = range_data[0][0]
            prev_type = range_data[0][1]
            for start_addr, range_type in ranges[1:]:
                ranges.append((prev_addr, start_addr, prev_type))
                prev_addr = start_addr
                prev_type = range_type
            ranges.append((prev_addr, 0xFFFFFFFF, prev_type))
            section_type_ranges[k] = ranges

        progress.log("i", "Built section type ranges.")

        progress = ProgressLine()
        for i, (
            sym_idx,
            (section_idx, name, value, sym_space, sym_base, override_type, size),
        ) in enumerate(sym_data.items()):
            progress.update(
                "Tabulating symbol data: processed {}/{} symbols ({:.0%})",
                i,
                len(sym_data),
                i / len(sym_data),
            )

            if override_type is not None:
                sym_type = override_type
            elif section_idx == rom_sh_idx:
                for start_addr, end_addr, sym_type in section_type_ranges[section_idx]:
                    if (value >= start_addr) and (value < end_addr):
                        break
                else:
                    raise ValueError(
                        "Could not resolve symbol ARM/Thumb/Data status for {} ({}+{:x})".format(
                            name, sym_space.upper(), value
                        )
                    )
            else:
                sym_type = SYM_TYPE_DATA

            symbols[sym_idx] = StoredSymbol(
                name, value - sym_base, size, sym_type, sym_space
            )
        progress.finish("Tabulated {} symbols", len(sym_data))
        break

    emit_syms = set(GET_SYMS).union(GET_RELOCS, GET_SHIM_RELOCS)
    target_syms = set(emit_syms)

    for override_sym in OVERRIDE_SYMS:
        for found_sym in symbols.values():
            if found_sym.name == override_sym.name:
                found_sym.offset = override_sym.offset
                found_sym.size = override_sym.size
                found_sym.space = override_sym.space
                found_sym.type = override_sym.type

    rom_sym_map = dict(
        (sym.address, sym)
        for sym in symbols.values()
        if (sym.space == "rom" and (sym.size is not None))
    )

    sorted_rom_addrs = sorted(rom_sym_map.keys())

    # Load relocation entries:
    progress = ProgressLine()
    relocs: List[StoredRelocation] = []
    for sh_idx, sh_header in enumerate(file.section_headers):
        if not (sh_header.is_rel or sh_header.is_rela):
            continue

        if sh_header.info == rom_sh_idx:
            rel_space = "rom"
            rel_section_data = rom_data
            rel_base_addr = 0x08000000
        else:
            continue

        if sh_header.is_rel:
            struct_fmt = "<II"
        else:
            struct_fmt = "<IIi"

        n_relocs = len(sh_header.data) // sh_header.ent_size
        for i, rel_struct in enumerate(struct.iter_unpack(struct_fmt, sh_header.data)):
            progress.update(
                "Processing relocation section {}: {}/{} relocations processed",
                sh_idx,
                i,
                n_relocs,
                i / n_relocs,
            )
            rel_offset = rel_struct[0]
            rel_info = rel_struct[1]
            if sh_header.is_rela:
                rel_addend = rel_struct[2]
            else:
                rel_addend = 0

            rel_sym_idx = (rel_info >> 8) & 0x00FFFFFF
            rel_type = rel_info & 0xFF

            # 40 is relocation type R_ARM_V4BX, which is used for ARMv4T interworking.
            # We can ignore this, since the GBA uses a v4T processor.
            if rel_type == 40:
                continue

            try:
                rel_sym = symbols[rel_sym_idx]
            except KeyError:
                continue

            if rel_sym.name.startswith("gCompressedText"):
                continue

            if rel_sym.name not in GET_RELOCS:
                idx = bisect.bisect_right(sorted_rom_addrs, rel_offset)
                if idx == 0:
                    continue

                other_sym = rom_sym_map[sorted_rom_addrs[idx - 1]]
                if rel_offset >= (other_sym.address + other_sym.size):
                    continue

                if other_sym.name not in GET_SHIM_RELOCS:
                    continue
                emit_syms.add(rel_sym.name)

            if rel_sym.space == "rom":
                sym_base = 0x08000000
            elif rel_sym.space == "wram":
                sym_base = 0x02000000

            rel_type_func = RELOCATION_TYPES[rel_type]
            rel_orig_field = rel_type_func.get_original_field(
                rel_section_data,
                rel_offset,
                rel_base_addr,
                rel_sym.offset,
                sym_base,
                rel_addend,
            )

            relocs.append(
                StoredRelocation(
                    rel_offset - rel_base_addr,
                    rel_sym.name,
                    rel_type,
                    rel_addend,
                    rel_orig_field,
                    rel_space,
                )
            )

        progress.finish("Processed {} relocations in section {}", n_relocs, sh_idx)

    ret_syms = [v for v in symbols.values() if v.name in emit_syms]

    for symbol in OVERRIDE_SYMS:
        if not any((s.name == symbol.name) for s in ret_syms):
            ret_syms.append(symbol)

    found_syms = set(v.name for v in ret_syms)
    missing_syms = target_syms - found_syms
    if len(missing_syms) > 0:
        print("Error - could not find symbols:", file=sys.stderr)
        for name in missing_syms:
            print(f"    {name}", file=sys.stderr)
        sys.exit(1)

    for sym in set(GET_SYMS).union(GET_RELOCS, GET_SHIM_RELOCS):
        pass

    return ret_syms, relocs


if __name__ == "__main__":
    symbols, relocs = read_data(ELF.load_file(sys.argv[1]))
    json.dump(
        {
            "symbols": list(map(asdict, symbols)),
            "relocations": list(map(asdict, relocs + EXTRA_RELOCS)),
        },
        sys.stdout,
    )
