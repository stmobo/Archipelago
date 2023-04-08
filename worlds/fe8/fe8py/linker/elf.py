from __future__ import annotations

import bisect
import json
import os.path as osp
import struct
from typing import Dict, Iterator, List, Optional, Tuple, Union

from .classes import (
    SECTION_TYPE_ROM,
    SECTION_TYPE_WRAM,
    SYM_TYPE_ARM,
    SYM_TYPE_DATA,
    SYM_TYPE_SECTION,
    SYM_TYPE_THUMB,
    SYM_TYPE_UNKNOWN,
    Section,
    Symbol,
)
from .relocation_types import RELOCATION_TYPES, RelocationType


class ELF:
    file: ELFFile
    bits_sections: Dict[int, Section]
    symbols: Dict[int, Dict[int, Symbol]]

    _reloc_idxs: List[int]

    def __init__(self, file: ELFFile):
        self.file = file
        self.bits_sections = {}
        self.symbols = {}
        self._reloc_idxs = []

        symtab_idxs: List[int] = []
        for sh_idx, sh_header in enumerate(file.section_headers):
            if sh_header.is_progbits or sh_header.is_nobits:
                self._load_bits_section(sh_idx, sh_header)
            elif sh_header.is_symbol_table:
                symtab_idxs.append(sh_idx)
            elif sh_header.is_rel or sh_header.is_rela:
                self._reloc_idxs.append(sh_idx)

        for sh_idx in symtab_idxs:
            self._load_symtab_section(sh_idx, self.file.section_headers[sh_idx])

    @classmethod
    def load_file(cls, fname: str) -> ELF:
        return cls(ELFFile.load_file(fname))

    def _load_bits_section(self, section_idx: int, section_header: ELFSectionHeader):
        section_name = section_header.name
        if section_name.startswith("."):
            section_name = section_name[1:]
        linked_name = self.file.name + ":" + section_name

        if section_name.startswith("wram") or section_name.startswith("bss"):
            section_type = SECTION_TYPE_WRAM
        else:
            section_type = SECTION_TYPE_ROM

        if section_header.is_progbits:
            if section_type != SECTION_TYPE_ROM:
                raise ValueError(
                    "Cannot link PROGBITS section {} into non-ROM memory".format(
                        linked_name
                    )
                )

            self.bits_sections[section_idx] = Section(
                linked_name,
                bytearray(section_header.data),
                section_type=SECTION_TYPE_ROM,
            )
        elif section_header.is_nobits:
            self.bits_sections[section_idx] = Section(
                linked_name, bytearray(section_header.size), section_type=section_type
            )

    def _load_symtab_section(self, symtab_idx: int, symtab_header: ELFSectionHeader):
        if not symtab_header.is_symbol_table:
            return

        type_ranges: Dict[int, Tuple[List[int], List[int]]] = {}
        sym_entries: List[Tuple[int, str, int, int, Optional[int], bool, int]] = []
        symtab_out = self.symbols.setdefault(symtab_idx, dict())

        for bits_idx in self.bits_sections.keys():
            type_ranges[bits_idx] = ([], [])

        cur_local_sym_file = self.file.name
        for sym_idx, (name_idx, value, size, info, bits_idx) in enumerate(
            symtab_header.iter_struct("IIIBxH")
        ):
            if sym_idx == 0:
                continue

            name = self.file.get_string(name_idx)
            if size == 0:
                size = None

            sym_binding = (info >> 4) & 0x0F
            sym_type = info & 0x0F
            if sym_binding == 0:  # local symbol
                if name == "$t":
                    range_starts, range_types = type_ranges[bits_idx]
                    range_starts.append(value)
                    range_types.append(SYM_TYPE_THUMB)
                elif name == "$a":
                    range_starts, range_types = type_ranges[bits_idx]
                    range_starts.append(value)
                    range_types.append(SYM_TYPE_ARM)
                elif name == "$d":
                    range_starts, range_types = type_ranges[bits_idx]
                    range_starts.append(value)
                    range_types.append(SYM_TYPE_DATA)
                elif sym_type == 4:  # file symbol
                    cur_local_sym_file = name
                elif sym_type == 3:
                    sym_entries.append(
                        (sym_idx, name, bits_idx, value, size, False, sym_type)
                    )
                elif sym_type in (0, 1, 2):
                    name = "__" + cur_local_sym_file + "_" + name
                    sym_entries.append(
                        (sym_idx, name, bits_idx, value, size, False, sym_type)
                    )
            elif bits_idx == 0xFFF1:  # SHN_ABS; symbol is absolute
                symtab_out[sym_idx] = Symbol(
                    name, value, None, size=size, weak_binding=(sym_binding == 2)
                )
            elif bits_idx == 0xFFF2:  # SHN_COMMON
                raise ValueError(
                    "Common symbols in ELF file {} are not supported".format(
                        self.file.name
                    )
                )
            elif bits_idx == 0:  # SHN_UNDEF
                symtab_out[sym_idx] = Symbol(
                    name,
                    None,
                    None,
                    sym_type=SYM_TYPE_UNKNOWN,
                    weak_binding=True,
                    size=size,
                )
            else:
                sym_entries.append(
                    (sym_idx, name, bits_idx, value, size, (sym_binding == 2), sym_type)
                )

        for bits_idx in list(type_ranges.keys()):
            # sort range_starts and range_types together, in order of ascending range start addresses
            range_starts, range_types = type_ranges[bits_idx]
            sorted_idxs = sorted(
                range(len(range_starts)), key=lambda i: range_starts[i]
            )
            type_ranges[bits_idx] = (
                [range_starts[i] for i in sorted_idxs],
                [range_types[i] for i in sorted_idxs],
            )

        for sym_idx, name, bits_idx, value, size, weak_binding, sym_type in sym_entries:
            try:
                bits_section = self.bits_sections[bits_idx]
            except KeyError:
                if sym_type == 3:
                    continue
                raise

            if sym_type == 2:
                if (value & 1) != 0:
                    resolved_type = SYM_TYPE_THUMB
                    value &= ~1
                else:
                    resolved_type = SYM_TYPE_ARM
            elif sym_type == 3:
                name = bits_section.name
                resolved_type = SYM_TYPE_SECTION
            elif (bits_section.type != SECTION_TYPE_ROM) or bits_section.name.endswith(
                "data"
            ):
                resolved_type = SYM_TYPE_DATA
            elif bits_idx in type_ranges:
                range_starts, range_types = type_ranges[bits_idx]
                range_idx = bisect.bisect_right(range_starts, value)

                if range_idx > 0:
                    resolved_type = range_types[range_idx - 1]
                else:
                    raise ValueError(
                        "Could not resolve ROM symbol ARM/Thumb/Data status for {} ({}+{:x})".format(
                            name, bits_section.name, value
                        )
                    )
            else:
                raise ValueError(
                    "Could not resolve ROM symbol ARM/Thumb/Data status for {} ({}+{:x})".format(
                        name, bits_section.name, value
                    )
                )

            symtab_out[sym_idx] = Symbol(
                name,
                value,
                bits_section,
                sym_type=resolved_type,
                weak_binding=weak_binding,
                size=size,
            )

            if sym_type == 3:
                bits_section.section_symbol = symtab_out[sym_idx]

    def _get_section_relocations(
        self, section_header: ELFSectionHeader
    ) -> Iterator[Tuple[Section, int, Symbol, RelocationType, int]]:
        if not (section_header.is_rel or section_header.is_rela):
            return

        sym_table = self.symbols[section_header.link]
        rel_section = self.bits_sections[section_header.info]

        if section_header.is_rel:
            fmt = "II"
        elif section_header.is_rela:
            fmt = "III"

        for rel_entry in section_header.iter_struct(fmt):
            rel_offset = rel_entry[0]
            rel_info = rel_entry[1]
            if section_header.is_rel:
                rel_addend = 0
            elif section_header.is_rela:
                rel_addend = rel_entry[2]

            rel_sym_idx = (rel_info >> 8) & 0x00FFFFFF
            rel_type = rel_info & 0xFF

            # 40 is relocation type R_ARM_V4BX, which is used for ARMv4T interworking.
            # We can ignore this, since the GBA uses a v4T processor.
            if rel_type == 40:
                continue

            yield (
                rel_section,
                rel_offset,
                sym_table[rel_sym_idx],
                RELOCATION_TYPES[rel_type],
                rel_addend,
            )

    def iter_relocations(
        self,
    ) -> Iterator[Tuple[Section, int, Symbol, RelocationType, int]]:
        for section_header in self.file.section_headers:
            if section_header.is_rel or section_header.is_rela:
                yield from self._get_section_relocations(section_header)

    def iter_symbols(self) -> Iterator[Symbol]:
        for symtab in self.symbols.values():
            yield from symtab.values()


class ELFSectionHeader:
    file: ELFFile
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

    def __init__(self, file: ELFFile, offset: int) -> None:
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

    def iter_struct(self, fmt: str) -> Iterator[Tuple[int, ...]]:
        if self.file.byte_order == "little":
            fmt = "<" + fmt
        else:
            fmt = ">" + fmt
        return struct.iter_unpack(fmt, self.data)

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


class ELFFile:
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

        if self.read_half(16) != 1:  # e_type, should be 1 for relocatable files
            raise ValueError("Invalid ELF file type " + str(self.read_half(16)))

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
    def load_file(cls, fname: str) -> ELFFile:
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
