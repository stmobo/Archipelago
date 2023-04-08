from __future__ import annotations

import bisect
import json
import os.path as osp
import struct
from typing import TYPE_CHECKING, Dict, Iterator, List, Optional, Tuple, Union

from ..rom_file import ROM_BASE_ADDRESS

if TYPE_CHECKING:
    from ..rom import ROM
    from ..rom_file import ROMFile
    from .linker import Linker
    from .relocation_types import RelocationType


SYM_TYPE_UNKNOWN = 0
SYM_TYPE_DATA = 1
SYM_TYPE_ARM = 2
SYM_TYPE_THUMB = 3
SYM_TYPE_SECTION = 4

SECTION_TYPE_ROM = 0
SECTION_TYPE_WRAM = 1


class Symbol:
    name: str
    offset: Optional[int]
    section: Optional[Section]
    type: int
    weak_binding: bool
    size: Optional[int]

    def __init__(
        self,
        name: str,
        offset: Optional[int],
        section: Optional[Section],
        sym_type: int = 0,
        weak_binding: bool = False,
        size: Optional[int] = None,
    ):
        assert name is not None

        self.name = name
        self.offset = offset
        self.section = section
        self.type = sym_type
        self.weak_binding = weak_binding
        self.size = size

    @property
    def address(self) -> int:
        if self.offset is None:
            raise ValueError("Symbol {} has no defined value".format(self.name))

        if self.section is None:
            return self.offset

        if self.section.load_address is None:
            raise ValueError(
                "Section for symbol {} has no load address".format(self.name)
            )
        return self.section.load_address + self.offset

    @property
    def fmt_offset(self) -> str:
        if self.offset is None:
            return "<undefined>"
        elif self.section is not None:
            return "{}+{:x}".format(self.section.name, self.offset)
        else:
            return format(self.offset, "x")

    def __str__(self) -> str:
        return self.name + " (" + self.fmt_offset + ")"

    def __eq__(self, other: Symbol) -> bool:
        if not isinstance(other, Symbol):
            return NotImplemented

        return (
            (self.name == other.name)
            and (self.offset == other.offset)
            and (self.section == other.section)
            and (self.type == other.type)
            and (self.weak_binding == other.weak_binding)
            and (self.size == other.size)
        )


class Section:
    name: str
    data: bytearray
    load_address: Optional[int]
    type: int
    section_symbol: Optional[Symbol]

    def __init__(
        self,
        name: str,
        data: bytearray,
        load_address: Optional[int] = None,
        section_type: int = 0,
        section_symbol: Optional[Symbol] = None,
    ):
        self.name = name
        self.data = data
        self.load_address = load_address
        self.type = section_type
        self.section_symbol = section_symbol

    @classmethod
    def from_rom_file(cls, rom: Union[ROM, ROMFile]) -> Section:
        try:
            rom = rom.file
        except AttributeError:
            pass

        return cls("ROM", rom.data, ROM_BASE_ADDRESS)

    def read_int(self, offset: int, size: int, *, signed: bool = False) -> int:
        return int.from_bytes(
            self.data[offset : offset + size], "little", signed=signed
        )


class Relocation:
    linker: Linker
    section: Section
    offset: int
    symbol_name: str
    reloc_type: RelocationType
    addend: int
    override_field: Optional[int]

    def __init__(
        self,
        linker: Linker,
        section: Section,
        offset: int,
        symbol_name: str,
        reloc_type: RelocationType,
        addend: int,
        *,
        override_field: Optional[int] = None
    ) -> None:
        self.linker = linker
        self.section = section
        self.offset = offset
        self.symbol_name = symbol_name
        self.reloc_type = reloc_type
        self.addend = addend
        self.override_field = override_field

    @property
    def symbol(self) -> Symbol:
        return self.linker.symbols[self.symbol_name]

    @property
    def fmt_offset(self) -> str:
        return "{}+{:x}".format(self.section.name, self.offset)

    def relocate(self, veneer: Optional[Symbol] = None):
        if veneer is None:
            actual_target_symbol = self.symbol
        else:
            actual_target_symbol = veneer

        new_data = self.reloc_type(
            self.section.data,
            self.offset,
            self.section.load_address,
            actual_target_symbol.address,
            self.addend,
            self.symbol.type,
            self.override_field,
        )

        prev_data = self.section.data[self.offset : self.offset + len(new_data)]
        if prev_data != new_data:
            self.section.data[self.offset : self.offset + len(new_data)] = new_data

            if not (
                (
                    self.symbol.section.name
                    in ("autogen_strtab", "autogen_symtab", "strings")
                )
                or (
                    self.section.name
                    in ("autogen_strtab", "autogen_symtab", "strings", "msgtab")
                )
            ):
                if veneer is None:
                    print(
                        "Relocating {} reference at {} pointing to {} ({}, address {:08x}, type {})".format(
                            self.reloc_type.name,
                            self.fmt_offset,
                            self.symbol.name,
                            self.symbol.fmt_offset,
                            self.symbol.address,
                            self.symbol.type,
                        )
                    )
                else:
                    print(
                        "Relocating {} reference at {} pointing to {} ({}, address {:08x}, type {}) via veneer at {} (address {:08x})".format(
                            self.reloc_type.name,
                            self.fmt_offset,
                            self.symbol.name,
                            self.symbol.fmt_offset,
                            self.symbol.address,
                            self.symbol.type,
                            veneer.fmt_offset,
                            veneer.address,
                        )
                    )
