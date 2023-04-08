from __future__ import annotations

import bisect
import json
import os.path as osp
import struct
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Union

from ..rom_file import ROM_BASE_ADDRESS, ROM_MAX_ADDRESS, ROM_MAX_SIZE
from . import relocation_types
from .classes import (
    SECTION_TYPE_ROM,
    SECTION_TYPE_WRAM,
    SYM_TYPE_ARM,
    SYM_TYPE_DATA,
    SYM_TYPE_THUMB,
    Relocation,
    Section,
    Symbol,
)
from .elf import ELF
from .relocation_types import RELOCATION_TYPES, RelocationOutOfRange, RelocationType
from .thumb_codegen import ThumbCodegen

if TYPE_CHECKING:
    from ..rom import ROM
    from ..rom_file import ROMFile


WRAM_BASE_ADDRESS = 0x02000000
WRAM_RESERVED_SPACE = 0x3F0FC  # bytes occupied by base game WRAM data
WRAM_MAX_ADDRESS = 0x02040000  # end of WRAM space

DESCRIPTOR_VERSION = 0


class Linker:
    rom: Section
    base_wram: Section

    extra_sections: List[Section]
    symbols: Dict[str, Symbol]
    relocations: Dict[Tuple[str, int], Relocation]

    def __init__(self, rom: Union[ROM, ROMFile]) -> None:
        self.rom = Section.from_rom_file(rom)
        self.base_wram = Section(
            "WRAM",
            bytearray(WRAM_RESERVED_SPACE),
            WRAM_BASE_ADDRESS,
            section_type=SECTION_TYPE_WRAM,
        )
        self.extra_sections = []
        self.symbols = {}
        self.relocations = {}

    def _add_symbol_obj(self, new_sym: Symbol) -> Symbol:
        if new_sym.name in self.symbols:
            old_sym = self.symbols[new_sym.name]
            if (new_sym.offset is None) or new_sym.weak_binding or (old_sym == new_sym):
                return old_sym
            elif (old_sym.offset is None) or old_sym.weak_binding:
                old_sym.offset = new_sym.offset
                old_sym.section = new_sym.section
                old_sym.type = new_sym.type
                old_sym.weak_binding = new_sym.weak_binding
                old_sym.size = new_sym.size

                if not new_sym.name.startswith("__"):
                    print(
                        "Bound undefined symbol {} to {} (type {}{})".format(
                            old_sym.name,
                            old_sym.fmt_offset,
                            old_sym.type,
                            ", weak binding" if old_sym.weak_binding else "",
                        )
                    )
                return old_sym
            else:
                raise ValueError(
                    "Found multiple definitions for symbol " + new_sym.name
                )
        else:
            self.symbols[new_sym.name] = new_sym
            if not new_sym.name.startswith("__"):
                print(
                    "Added new symbol {} ({}, type {}{})".format(
                        new_sym.name,
                        new_sym.fmt_offset,
                        new_sym.type,
                        ", weak binding" if new_sym.weak_binding else "",
                    )
                )
            return new_sym

    def add_symbol(
        self,
        name: str,
        offset: Optional[int],
        section: Optional[Section],
        sym_type: int = 0,
        weak_binding: bool = False,
        size: Optional[int] = None,
    ) -> Symbol:
        return self._add_symbol_obj(
            Symbol(
                name,
                offset,
                section,
                sym_type=sym_type,
                weak_binding=weak_binding,
                size=size,
            )
        )

    def add_rom_symbol(
        self,
        name: str,
        offset: int,
        sym_type: int = 0,
        size: Optional[int] = None,
        weak_binding: bool = False,
    ) -> Symbol:
        return self.add_symbol(
            name,
            offset,
            self.rom,
            sym_type=sym_type,
            size=size,
            weak_binding=weak_binding,
        )

    def replace_symbol(self, name: str, replacement: Symbol, rename_to: str) -> Symbol:
        old_symbol = self.symbols[name]
        old_symbol.name = rename_to
        self.symbols[rename_to] = old_symbol
        try:
            del self.symbols[replacement.name]
        except KeyError:
            pass
        replacement.name = name
        self.symbols[name] = replacement
        return old_symbol

    def add_section(
        self,
        name: str,
        data: bytearray,
        symbols: Optional[Dict[str, int]] = None,
        section_type: int = 0,
    ) -> Section:
        section = Section(name, bytearray(data), section_type=section_type)
        if symbols is not None:
            for name, offset in symbols.items():
                self.add_symbol(name, offset, section)
        self.extra_sections.append(section)
        return section

    def add_relocation(
        self,
        section: Section,
        offset: int,
        symbol_name: Union[str, Symbol],
        reloc_type: RelocationType,
        addend: int = 0,
        *,
        override_field: Optional[int] = None,
    ):
        if isinstance(symbol_name, Symbol):
            symbol_name = symbol_name.name

        assert symbol_name is not None

        reloc_key = (section.name, offset)
        self.relocations[reloc_key] = Relocation(
            self,
            section,
            offset,
            symbol_name,
            reloc_type,
            addend,
            override_field=override_field,
        )

    def add_rom_relocation(
        self,
        offset: int,
        symbol_name: Union[str, Symbol],
        reloc_type: RelocationType,
        addend: int = 0,
    ):
        return self.add_relocation(self.rom, offset, symbol_name, reloc_type, addend)

    def replace_with_trampoline(
        self,
        target_sym: str,
        dest_sym: str | Symbol,
        scratch_register: str | int | None = None,
    ):
        target_sym: Symbol = self.symbols[target_sym]
        target_start = target_sym.offset

        trampoline_gen = ThumbCodegen((target_start & 2) == 0).inline_trampoline(
            dest_sym, scratch_register=scratch_register
        )
        trampoline_gen.finalize_to(self, target_sym.section, target_start)

        print(
            "    Generated {}-byte trampoline to {} at {}".format(
                len(trampoline_gen.data), str(dest_sym), target_sym.fmt_offset
            )
        )

    def duplicate_and_shim_thumb(
        self,
        target_sym: str,
        shim_before_sym: Optional[str | Symbol] = None,
        shim_after_sym: Optional[str | Symbol] = None,
    ):
        target_sym: Symbol = self.symbols[target_sym]
        target_section = target_sym.section
        target_start = target_sym.offset

        if target_sym.size is None:
            raise ValueError("Cannot install shim for function with unknown length")

        # Copy the entire function to a new section
        target_end = target_start + target_sym.size
        copy_data = bytearray()
        if (target_start & 2) != 0:
            copy_data.extend(b"\xe4\x46")
            copy_start = 2
        else:
            copy_start = 0
        copy_data.extend(target_section.data[target_start:target_end])

        copy_section = self.add_section(
            "autogen_" + target_sym.name + "_copy",
            copy_data,
            section_type=SECTION_TYPE_ROM,
        )
        self.add_symbol(
            "__" + target_sym.name + "_copy",
            0,
            copy_section,
            sym_type=SYM_TYPE_THUMB,
            size=target_sym.size,
        )

        print(
            "Creating {}-byte copy of {} ({})...".format(
                len(copy_data), target_sym.name, target_sym.fmt_offset
            )
        )

        # Collect all relocations in the original function
        # Keyed by original offset => relocation
        adjust_relocs: Dict[int, Relocation] = {}
        for (reloc_section, reloc_offset), reloc in self.relocations.items():
            if (
                (reloc_section != target_section.name)
                or (reloc_offset < target_start)
                or (reloc_offset >= target_end)
            ):
                continue
            adjust_relocs[reloc_offset] = reloc

        # copy relocations to new function
        for old_reloc_offset, reloc in adjust_relocs.items():
            new_reloc_offset = (old_reloc_offset - target_start) + copy_start
            print(
                "    Moving {} relocation at {} to {}+{:x} (target {} / {})".format(
                    reloc.reloc_type.name,
                    reloc.fmt_offset,
                    copy_section.name,
                    new_reloc_offset,
                    reloc.symbol_name,
                    reloc.symbol.fmt_offset,
                )
            )

            del self.relocations[(target_section.name, old_reloc_offset)]
            self.add_relocation(
                copy_section,
                new_reloc_offset,
                reloc.symbol_name,
                reloc.reloc_type,
                reloc.addend,
                override_field=reloc.override_field,
            )

        # Generate an entry trampoline
        shim_internal_name = "__" + target_sym.name + "_shim"
        entry_codegen = (
            ThumbCodegen((target_start & 2) == 0)
            .push("r0", "r1", "r2", "r3", "lr")
            .inline_trampoline(shim_internal_name, scratch_register="r0")
        )
        entry_codegen.finalize_to(self, target_section, target_start)

        print(
            "    Generated {}-byte entry trampoline at {}".format(
                len(entry_codegen.data), target_sym.fmt_offset
            )
        )

        shim_codegen = ThumbCodegen().symbol(shim_internal_name)
        if shim_before_sym is not None:
            # mov r0, sp
            # call user function
            # cmp r0, #0
            # beq continue_to_original
            # pop {r0, r1, r2, r3, pc}
            # continue_to_original: load r0-r3 from stack w/o popping
            #
            # This will break when shimming functions that expect arguments
            # passed via the stack, but that shouldn't be a problem for most
            # functions.
            shim_codegen.mov("r0", "sp").call(shim_before_sym).add_instructions(
                b"\x00\x28"
            ).local_cond_jump("eq", "continue_to_original").pop(
                "r0", "r1", "r2", "r3", "pc"
            ).label(
                "continue_to_original"
            ).add_instructions(
                b"\x00\x98\x01\x99\x02\x9a\x03\x9b"
            )
        else:
            # load r0 from stack w/o popping
            shim_codegen.add_instructions(b"\x00\x98")

        shim_codegen.call("__" + target_sym.name + "_copy")

        if shim_after_sym is not None:
            # mov r1, sp
            # call user function
            # pop {r0, r1, r2, r3, pc}
            shim_codegen.mov("r1", "sp").call(shim_after_sym).pop(
                "r0", "r1", "r2", "r3", "pc"
            )
        else:
            # add sp, #16
            # pop {pc}
            shim_codegen.add_instructions(b"\x04\xb0").pop("pc")

        shim_section = shim_codegen.finalize(
            self, "autogen_" + target_sym.name + "_shim"
        )

        print(
            "    Generated {}-byte shim helper".format(
                len(shim_section.data),
            )
        )

    def get_symbol_address(self, name: str) -> int:
        return self.symbols[name].address

    def link(self) -> bytearray:
        cur_rom_addr = ROM_BASE_ADDRESS + len(self.rom.data)
        cur_wram_addr = WRAM_BASE_ADDRESS + WRAM_RESERVED_SPACE

        def _assign_section_addr(section: Section) -> Section:
            nonlocal cur_rom_addr, cur_wram_addr

            if section.type == SECTION_TYPE_ROM:
                # align section load addresses to 4 bytes
                if (cur_rom_addr & 3) != 0:
                    cur_rom_addr = (cur_rom_addr & ~3) + 4
                section.load_address = cur_rom_addr
                cur_rom_addr += len(section.data)

                if cur_rom_addr > ROM_MAX_ADDRESS:
                    raise ValueError(
                        "Linked data exceeds ROM size ({:x} bytes over limit)".format(
                            ROM_MAX_ADDRESS - cur_rom_addr
                        )
                    )

                print(
                    "Linking extra section {} at ROM address {:08x}".format(
                        section.name, section.load_address
                    )
                )
            elif section.type == SECTION_TYPE_WRAM:
                if (cur_wram_addr & 3) != 0:
                    cur_wram_addr = (cur_wram_addr & ~3) + 4
                section.load_address = cur_wram_addr
                cur_wram_addr += len(section.data)

                if cur_wram_addr > WRAM_MAX_ADDRESS:
                    raise ValueError(
                        "Linked data exceeds WRAM size ({:x} bytes over limit)".format(
                            WRAM_MAX_ADDRESS - cur_wram_addr
                        )
                    )

                print(
                    "Linking extra section {} at WRAM address {:08x}".format(
                        section.name, section.load_address
                    )
                )
            else:
                raise ValueError(
                    "Unknown type {} for section {}".format(section.type, section.name)
                )

            return section

        # Generate symbol and strings tables.
        # The only remaining sections and symbols being added from this point on are autogenerated,
        # so they don't need to go into the tables.

        # Symbol table layout:
        # 00 - Memory address of symbol 1
        # 04 - Memory address of name string for symbol 1
        # 08 - Size of symbol 1 (or 0 if size not known)
        # ...

        # Strings are stored as a two-byte string length,
        # followed by the string characters (ASCII, no null terminator).
        # Each string starts on a 2-aligned address.

        symtab = self.add_section(
            "autogen_symtab", bytearray(), section_type=SECTION_TYPE_ROM
        )
        strtab = self.add_section(
            "autogen_strtab", bytearray(), section_type=SECTION_TYPE_ROM
        )
        strtab_indices: Dict[str, int] = {}
        n_symtab_entries = 0

        for name, symbol in self.symbols.items():
            if symbol.section is None or symbol.offset is None:
                raise ValueError("Symbol {} is undefined".format(name))

            if (
                name.startswith("__")
                or name.startswith("autogen")
                or symbol.section.name.startswith("autogen")
            ):
                continue

            try:
                str_idx = strtab_indices[name]
            except KeyError:
                str_idx = len(strtab_indices)
                strtab_indices[name] = str_idx

            if symbol.size is not None:
                sz = symbol.size
            else:
                sz = 0

            cur_symtab_offset = len(symtab.data)
            symtab.data.extend(struct.pack("<III", 0, 0, sz))
            self.add_relocation(
                symtab, cur_symtab_offset, symbol, relocation_types.ABSOLUTE_32
            )
            self.add_relocation(
                symtab,
                cur_symtab_offset + 4,
                "__autogen_strtab_entry_" + str(str_idx),
                relocation_types.ABSOLUTE_32,
            )

            n_symtab_entries += 1

        # populate strtab and add autogenerated symbols for relocation
        for name, idx in strtab_indices.items():
            # ensure the length field is 2-aligned
            if (len(strtab.data) & 1) != 0:
                strtab.data.append(0)

            encoded = name.encode("ascii")
            encoded = len(encoded).to_bytes(2, "little", signed=False) + encoded
            self.add_symbol(
                "__autogen_strtab_entry_" + str(idx),
                len(strtab.data),
                strtab,
                sym_type=SYM_TYPE_DATA,
                size=len(encoded),
            )
            strtab.data.extend(encoded)

        # insert the descriptor block at the very start of new data, which
        # should ensure that it's at a known position in memory
        descriptor_block = Section(
            "rom_descriptor", bytearray(0x1C), section_type=SECTION_TYPE_ROM
        )
        self.extra_sections.insert(0, descriptor_block)

        # Descriptor block layout:
        # 00 - Header bytes (DE C0 AD DE)
        # 04 - Version (2 bytes)
        # 06 - padding
        # 08 - start of unoccupied ROM space
        # 0C - Memory address of symbol table
        # 10 - # of entries in symbol table
        # 14 - Memory address of string table
        # 18 - Length of string table in bytes
        descriptor_block.data[:4] = (0xDEADC0DE).to_bytes(4, "little", signed=False)
        descriptor_block.data[4:6] = DESCRIPTOR_VERSION.to_bytes(
            2, "little", signed=False
        )

        descriptor_block.data[0x10:0x14] = n_symtab_entries.to_bytes(
            4, "little", signed=False
        )

        self.add_relocation(
            descriptor_block,
            0x0C,
            self.add_symbol(
                "__autogen_symtab_start",
                0,
                symtab,
                sym_type=SYM_TYPE_DATA,
                size=len(symtab.data),
            ),
            relocation_types.ABSOLUTE_32,
        )

        self.add_relocation(
            descriptor_block,
            0x14,
            self.add_symbol(
                "__autogen_strtab_start",
                0,
                strtab,
                sym_type=SYM_TYPE_DATA,
                size=len(strtab.data),
            ),
            relocation_types.ABSOLUTE_32,
        )

        descriptor_block.data[0x18:0x1C] = len(strtab.data).to_bytes(
            4, "little", signed=False
        )

        for section in self.extra_sections:
            _assign_section_addr(section)

        assert descriptor_block.load_address == 0x09000000

        veneer_section: Section = _assign_section_addr(
            Section("autogen_veneer", bytearray(), section_type=SECTION_TYPE_ROM)
        )

        # Perform relocations
        for relocation in self.relocations.values():
            try:
                relocation.relocate()
            except RelocationOutOfRange:
                # Attempt to generate a transparent veneer to the symbol
                if relocation.reloc_type.veneer_type == "thumb":
                    veneer_name = "__autogen_veneer_thumb_" + relocation.symbol_name
                elif relocation.reloc_type.veneer_type == "arm":
                    veneer_name = "__autogen_veneer_arm_" + relocation.symbol_name
                else:
                    raise ValueError(
                        "Cannot generate veneer for relocation type {} with unknown veneer type".format(
                            relocation.reloc_type.name
                        )
                    )

                if veneer_name not in self.symbols:
                    dest_symbol = relocation.symbol

                    if relocation.symbol.type == SYM_TYPE_ARM:
                        dest_address = dest_symbol.address
                    elif relocation.symbol.type == SYM_TYPE_THUMB:
                        dest_address = dest_symbol.address | 1
                    else:
                        raise ValueError(
                            "Cannot generate veneer for symbol {} with unknown type".format(
                                relocation.symbol_name
                            )
                        )

                    if relocation.reloc_type.veneer_type == "thumb":
                        # push {r4, lr}
                        # ldr r4, [pc, #4]
                        # str r4, [sp, #4]
                        # pop {r4, pc}
                        # .word TargetAddress
                        codegen = (
                            ThumbCodegen()
                            .push("r4", "lr")
                            .load_pc_relative("r4", 4)
                            .store_sp_relative("r4", 4)
                            .pop("r4", "pc")
                            .add_instructions(
                                dest_address.to_bytes(4, "little", signed=False)
                            )
                        )
                        veneer_code = codegen.data
                        veneer_sym_type = SYM_TYPE_THUMB
                    elif relocation.reloc_type.veneer_type == "arm":
                        # push {ip, lr}
                        # add lr, pc, #4
                        # ldr ip, [pc, #4]
                        # bx ip
                        # pop {ip, pc}
                        # .word TargetAddress
                        veneer_code = b"\x00\x50\x2d\xe9\x04\xe0\x8f\xe2\x04\xc0\x9f\xe5\x1c\xff\x2f\xe1\x00\x90\xbd\xe8"
                        veneer_code += dest_address.to_bytes(4, "little", signed=False)
                        veneer_sym_type = SYM_TYPE_ARM

                    veneer_sym = self.add_symbol(
                        veneer_name,
                        len(veneer_section.data),
                        veneer_section,
                        veneer_sym_type,
                        size=len(veneer_code),
                    )

                    # print(
                    #     "Generated veneer for symbol {} at {} (address {:08x}) for relocation at {:08x}".format(
                    #         dest_symbol.name,
                    #         veneer_sym.fmt_offset,
                    #         veneer_sym.address,
                    #         relocation.section.load_address + relocation.offset,
                    #     )
                    # )

                    veneer_section.data.extend(veneer_code)
                else:
                    veneer_sym = self.symbols[veneer_name]

                relocation.relocate(veneer_sym)

        if len(veneer_section.data) > 0:
            self.extra_sections.append(veneer_section)
            cur_rom_addr += len(veneer_section.data)

        # Put all of the sections together
        out_buf = bytearray(cur_rom_addr - ROM_BASE_ADDRESS)
        out_buf[: len(self.rom.data)] = self.rom.data
        for section in self.extra_sections:
            # only ROM sections should appear in the final output
            if section.type != SECTION_TYPE_ROM:
                continue
            offset = section.load_address - ROM_BASE_ADDRESS
            out_buf[offset : offset + len(section.data)] = section.data

        # Fill in the first unoccupied ROM address within the descriptor block:
        last_rom_addr = ROM_BASE_ADDRESS + len(out_buf)
        last_rom_addr = (last_rom_addr & ~3) + 4
        out_buf[0x01000008:0x0100000C] = last_rom_addr.to_bytes(
            4, "little", signed=False
        )

        assert len(out_buf) <= ROM_MAX_SIZE

        # Display link results
        sorted_syms = sorted(
            self.symbols.items(),
            key=lambda kv: (kv[1].type, -kv[1].address),
            reverse=True,
        )
        max_offset_len = max(len(sym.fmt_offset) for _, sym in sorted_syms)
        max_name_len = max(len(sym.name) for _, sym in sorted_syms)

        print("\n[ Symbol Table ]")
        print("Address  {} Size Bind Typ Name".format("Offset".ljust(max_offset_len)))
        for name, symbol in sorted_syms:
            if (
                name.startswith("__gMsgString_")
                or name.startswith("__autogen_")
                or name.startswith("__Event_")
            ):
                continue

            if symbol.type == SYM_TYPE_DATA:
                type_str = "DAT"
            elif symbol.type == SYM_TYPE_ARM:
                type_str = "ARM"
            elif symbol.type == SYM_TYPE_THUMB:
                type_str = "THM"
            else:
                type_str = "???"

            if symbol.size is None:
                size_str = " -- "
            else:
                size_str = format(symbol.size, "04x")

            if symbol.weak_binding:
                bind_str = "WEAK"
            else:
                bind_str = "    "

            print(
                "{:08x} {} {} {} {} {}".format(
                    symbol.address,
                    symbol.fmt_offset.ljust(max_offset_len),
                    size_str,
                    bind_str,
                    type_str,
                    name.ljust(max_name_len),
                )
            )

        return out_buf

    def load_external_data(self, filename: str):
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)

        for symbol in data["symbols"]:
            if symbol["space"] == "rom":
                section = self.rom
            elif symbol["space"] == "wram":
                section = self.base_wram

            self.add_symbol(
                symbol["name"],
                symbol["offset"],
                section,
                sym_type=symbol["type"],
                weak_binding=True,
                size=symbol["size"],
            )

        for reloc in data["relocations"]:
            self.add_relocation(
                self.rom,
                reloc["offset"],
                reloc["symbol_name"],
                RELOCATION_TYPES[reloc["type"]],
                reloc["addend"],
                override_field=reloc["original_field"],
            )

    def load_elf(self, fname: str):
        file = ELF.load_file(fname)

        for section in file.bits_sections.values():
            if section.type == SECTION_TYPE_ROM:
                space = "ROM"
            elif section.type == SECTION_TYPE_WRAM:
                space = "WRAM"
            else:
                raise ValueError(
                    "Unknown type {} for section {}".format(section.type, section.name)
                )

            self.extra_sections.append(section)
            print(
                "Loaded section {} ({}, size {:x})".format(
                    section.name, space, len(section.data)
                )
            )

        for symbol in file.iter_symbols():
            self._add_symbol_obj(symbol)

        for (
            reloc_section,
            reloc_offset,
            target_symbol,
            reloc_type,
            reloc_addend,
        ) in file.iter_relocations():
            self.add_relocation(
                reloc_section,
                reloc_offset,
                target_symbol.name,
                reloc_type,
                addend=reloc_addend,
            )
