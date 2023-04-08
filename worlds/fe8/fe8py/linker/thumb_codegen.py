from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional, Tuple

from . import relocation_types
from .classes import SECTION_TYPE_ROM, SYM_TYPE_THUMB, Section, Symbol

if TYPE_CHECKING:
    from .linker import Linker
    from .relocation_types import RelocationType

CONDITION_EQ = 0b0000  # equal
CONDITION_NE = 0b0001  # not equal
CONDITION_CS = CONDITION_HS = 0b0010  # unsigned higher or same / carry set
CONDITION_CC = CONDITION_LO = 0b0011  # unsigned lower / carry clear
CONDITION_MI = 0b0100  # minus / negative
CONDITION_PL = 0b0101  # plus / positive or zero
CONDITION_VS = 0b0110  # overflow
CONDITION_VC = 0b0111  # no overflow
CONDITION_HI = 0b1000  # unsigned higher
CONDITION_LS = 0b1001  # unsigned lower or same
CONDITION_GE = 0b1010  # signed greater than or equal
CONDITION_LT = 0b1011  # signed less than
CONDITION_GT = 0b1100  # signed greater than
CONDITION_LE = 0b1101  # signed less than or equal
CONDITION_AL = 0b1110  # always

CONDITIONS = {
    "eq": CONDITION_EQ,
    "ne": CONDITION_NE,
    "cs": CONDITION_CS,
    "hs": CONDITION_CS,
    "cc": CONDITION_CC,
    "lo": CONDITION_CC,
    "mi": CONDITION_MI,
    "pl": CONDITION_PL,
    "vs": CONDITION_VS,
    "vc": CONDITION_VC,
    "hi": CONDITION_HI,
    "ls": CONDITION_LS,
    "ge": CONDITION_GE,
    "lt": CONDITION_LT,
    "gt": CONDITION_GT,
    "le": CONDITION_LE,
    "al": CONDITION_AL,
}


def _ensure_register(register: int | str) -> int:
    if isinstance(register, str):
        register = register.strip().lower()
        if register.startswith("r"):
            register = int(register[1:])
        elif register == "pc":
            return 15
        elif register == "lr":
            return 14
        elif register == "sp":
            return 13
        elif register == "ip":
            return 12
    if not isinstance(register, int):
        raise TypeError(
            "register must be of type int or str, got " + type(register).__name__
        )
    if (register < 0) or (register >= 16):
        raise ValueError("Invalid register number " + str(register))
    return register


def _ensure_low_register(register: int | str) -> int:
    register = _ensure_register(register)
    if register >= 8:
        raise ValueError(
            "Instruction register must be a low register (got r{}, expected r0-r7)".format(
                register
            )
        )
    return register


class Literal:
    value: int
    register: int

    def __init__(self, value: int, register: int):
        self.value = value
        self.register = register

    def gen_instruction(self, place: int, target_place: int) -> bytes:
        assert (target_place & 3) == 0
        aligned_pc = (place + 4) & ~3
        offset = (target_place - aligned_pc) >> 2
        assert offset >= 0
        assert offset < 0x100
        return ((0b01001 << 11) | (self.register << 8) | offset).to_bytes(
            2, "little", signed=False
        )


class AbsoluteRef:
    symbol_name: str
    register: int

    def __init__(self, symbol_name: str, register: int):
        self.symbol_name = symbol_name
        self.register = register

    def gen_instruction(self, place: int, target_place: int) -> bytes:
        assert (target_place & 3) == 0
        aligned_pc = (place + 4) & ~3
        offset = (target_place - aligned_pc) >> 2
        assert offset >= 0
        assert offset < 0x100
        return ((0b01001 << 11) | (self.register << 8) | offset).to_bytes(
            2, "little", signed=False
        )


class Branch:
    symbol_name: str
    reloc_type: RelocationType

    def __init__(self, symbol_name: str, reloc_type: RelocationType):
        self.symbol_name = symbol_name
        self.reloc_type = reloc_type


class LocalBranch:
    label: str
    condition: Optional[int]

    def __init__(self, label: str, condition: Optional[int] = None):
        if (condition is not None) and not isinstance(condition, int):
            condition = CONDITIONS[condition]
        self.label = label
        self.condition = condition

    def gen_instruction(self, place: int, target_place: int) -> bytes:
        offset = (target_place - (place + 4)) >> 1

        if self.condition is not None:
            hi = ((0b1101 << 4) | self.condition).to_bytes(1, "little", signed=False)
            lo = offset.to_bytes(1, "little", signed=True)
            return lo + hi
        else:
            if offset < 0:
                offset = (offset + (1 << 11)) | (1 << 10)
            assert (offset & ~((1 << 11) - 1)) == 0
            return ((0b11100 << 11) | offset).to_bytes(2, "little", signed=False)


class ThumbCodegen:
    data: bytearray
    symbols: Dict[str, int]
    extra_relocations: Dict[int, Tuple[str, RelocationType]]
    refs: Dict[int, Literal | AbsoluteRef | Branch | LocalBranch]
    labels: Dict[str, int]
    starts_aligned: bool
    _finalized: bool

    def __init__(self, starts_aligned: bool = True):
        self.data = bytearray()
        self.symbols = {}
        self.extra_relocations = {}
        self.refs = {}
        self.labels = {}
        self.starts_aligned = starts_aligned
        self._finalized = False

    def _ensure_not_finalized(self):
        if self._finalized:
            raise ValueError("Codegen object has been finalized already")

    @property
    def cur_position(self) -> int:
        return len(self.data)

    @property
    def word_aligned(self) -> bool:
        return ((self.cur_position & 2) == 0) == self.starts_aligned

    def add_symbol(self, name: str, offset: int):
        self.symbols[name] = offset

    def symbol(self, name: str, offset: int = 0) -> ThumbCodegen:
        self.add_symbol(name, offset + self.cur_position)
        return self

    def add_relocation(self, name: str, reloc_type: RelocationType, offset: int):
        self.extra_relocations[offset] = (name, reloc_type)

    def relocation(
        self, name: str, reloc_type: RelocationType, offset: int = 0
    ) -> ThumbCodegen:
        self.add_relocation(name, reloc_type, self.cur_position + offset)
        return self

    def add_instructions(self, *insts: bytes | bytearray | int) -> ThumbCodegen:
        self._ensure_not_finalized()
        for inst in insts:
            if isinstance(inst, int):
                if inst > 0xFFFF:
                    inst = inst.to_bytes(4, "little", signed=False)
                else:
                    inst = inst.to_bytes(2, "little", signed=False)
            assert (len(inst) & 1) == 0
            self.data.extend(inst)
        return self

    def fill(self, n: int) -> ThumbCodegen:
        self._ensure_not_finalized()
        self.data.extend(b"\0" * n)
        return self

    def nop(self) -> ThumbCodegen:
        # This encodes a `mov r12, r12` instruction, which has the advantage of not messing with condition flags.
        return self.add_instructions(b"\xe4\x46")

    def load_literal(self, register: int | str, value: int) -> ThumbCodegen:
        """Adds a `ldr [register], =value` instruction."""
        self.refs[self.cur_position] = Literal(value, _ensure_low_register(register))
        return self.fill(2)

    def load_symbol(self, register: int | str, symbol: str | Symbol) -> ThumbCodegen:
        """Adds a `ldr [register], =symbol` instruction."""
        if not isinstance(symbol, str):
            symbol = symbol.name
        self.refs[self.cur_position] = AbsoluteRef(
            symbol, _ensure_low_register(register)
        )
        return self.fill(2)

    def call(self, symbol: str | Symbol) -> ThumbCodegen:
        """Adds a `bl [symbol]` instruction."""
        if not isinstance(symbol, str):
            symbol = symbol.name
        self.refs[self.cur_position] = Branch(symbol, relocation_types.R_ARM_THM_CALL)
        return self.add_instructions(b"\xff\xf7\xfe\xff")

    def jump(self, symbol: str | Symbol) -> ThumbCodegen:
        """Adds a `b [symbol]` instruction."""
        if not isinstance(symbol, str):
            symbol = symbol.name
        self.refs[self.cur_position] = Branch(symbol, relocation_types.R_ARM_THM_JUMP11)
        return self.add_instructions(b"\xfe\xe7")

    def cond_jump(self, condition: int | str, symbol: str | Symbol) -> ThumbCodegen:
        """Adds a `b<cond> [symbol]` instruction."""
        if not isinstance(symbol, str):
            symbol = symbol.name
        if not isinstance(condition, int):
            condition = CONDITIONS[condition]

        assert (condition > 0) and (condition < 0b1110)
        self.refs[self.cur_position] = Branch(symbol, relocation_types.R_ARM_THM_JUMP8)
        return self.add_instructions((0b1101 << 12) | (condition << 8) | 0xFE)

    def branch_exchange(self, register: int | str) -> ThumbCodegen:
        """Adds a `bx [register]` instruction."""
        return self.add_instructions(
            (0b01000111 << 8) | (_ensure_register(register) << 3)
        )

    def local_jump(self, label: str) -> ThumbCodegen:
        self.refs[self.cur_position] = LocalBranch(label)
        return self.add_instructions(b"\xfe\xe7")

    def local_cond_jump(self, condition: int | str, label: str) -> ThumbCodegen:
        self.refs[self.cur_position] = LocalBranch(label, condition)
        return self.add_instructions(b"\0\0")

    def label(self, label: str, offset: int = 0) -> ThumbCodegen:
        self.labels[label] = self.cur_position + offset
        return self

    def mov(self, dst: int | str, src: int | str) -> ThumbCodegen:
        dst = _ensure_register(dst)
        src = _ensure_register(src)

        if (dst <= 7) and (src <= 7):
            return self.add_instructions((0b0001110 << 9) | (src << 3) | dst)
        else:
            msb_d = dst & 8
            msb_s = src & 8
            return self.add_instructions(
                (0b01000110 << 8)
                | (msb_d << 4)
                | (msb_s << 3)
                | ((src & 7) << 3)
                | (dst & 7)
            )

    def push(self, *registers: int | str) -> ThumbCodegen:
        reglist = 0
        for reg in map(_ensure_register, registers):
            if reg <= 7:
                reglist |= 1 << reg
            elif reg == 14:  # push lr
                reglist |= 1 << 8
            else:
                raise ValueError("cannot push register r" + str(reg))
        return self.add_instructions((0b1011010 << 9) | reglist)

    def pop(self, *registers: int | str) -> ThumbCodegen:
        reglist = 0
        for reg in map(_ensure_register, registers):
            if reg <= 7:
                reglist |= 1 << reg
            elif reg == 15:  # pop pc
                reglist |= 1 << 8
            else:
                raise ValueError("cannot pop register r" + str(reg))
        return self.add_instructions((0b1011110 << 9) | reglist)

    def store_sp_relative(self, src: int | str, offset: int) -> ThumbCodegen:
        src = _ensure_low_register(src)
        assert (offset & 3) == 0

        offset >>= 2
        assert offset < 256

        return self.add_instructions((0b10010 << 11) | (src << 8) | offset)

    def load_sp_relative(self, dst: int | str, offset: int) -> ThumbCodegen:
        dst = _ensure_low_register(dst)
        assert (offset & 3) == 0

        offset >>= 2
        assert offset < 256

        return self.add_instructions((0b10011 << 11) | (dst << 8) | offset)

    def load_pc_relative(self, dst: int | str, offset: int) -> ThumbCodegen:
        dst = _ensure_low_register(dst)
        assert (offset & 3) == 0

        offset >>= 2
        assert offset < 256

        return self.add_instructions((0b01001 << 11) | (dst << 8) | offset)

    def trampoline(
        self, dest_symbol: str | Symbol, *, scratch_register: Optional[str | int] = None
    ) -> ThumbCodegen:
        if scratch_register is not None:
            scratch_register = _ensure_low_register(scratch_register)
            return self.load_symbol(scratch_register, dest_symbol).branch_exchange(
                scratch_register
            )
        else:
            return self.push("r0").load_symbol("r0", dest_symbol).branch_exchange("r0")

    def inline_trampoline(
        self, dest_symbol: str | Symbol, *, scratch_register: Optional[str | int] = None
    ) -> ThumbCodegen:
        if not isinstance(dest_symbol, str):
            dest_symbol = dest_symbol.name

        if scratch_register is not None:
            scratch_register = _ensure_low_register(scratch_register)
        else:
            self.push("r0")
            scratch_register = 0

        ldr = (0b01001 << 11) | (scratch_register << 8)
        fill = b"\0\0\0\0"
        if not self.word_aligned:
            ldr |= 1
            fill += b"\0\0"

        return (
            self.add_instructions(ldr)
            .branch_exchange(scratch_register)
            .add_instructions(fill)
            .relocation(dest_symbol, relocation_types.ABSOLUTE_32, -4)
        )

    def ensure_aligned(self) -> ThumbCodegen:
        if not self.word_aligned:
            return self.nop()
        return self

    def finalize_to(self, linker: Linker, section: Section, start_offset: int):
        self._ensure_not_finalized()
        self._finalized = True

        literals: Dict[int, int] = {}
        sym_literals: Dict[str, int] = {}

        for ref in self.refs.values():
            if isinstance(ref, Literal):
                literals[ref.value] = None
            elif isinstance(ref, AbsoluteRef):
                sym_literals[ref.symbol_name] = None

        if ((len(literals) > 0) or (len(sym_literals) > 0)) and not self.word_aligned:
            # Ensure literals are aligned to 4 bytes
            self.data.extend(b"\0\0")

        for value in list(literals.keys()):
            literals[value] = self.cur_position
            self.data.extend(value.to_bytes(4, "little", signed=(value < 0)))

        for name in list(sym_literals.keys()):
            pos = self.cur_position
            sym_literals[name] = pos
            self.data.extend(b"\0\0\0\0")
            linker.add_relocation(
                section, start_offset + pos, name, relocation_types.ABSOLUTE_32
            )

        for place, ref in self.refs.items():
            if isinstance(ref, Literal):
                self.data[place : place + 4] = ref.gen_instruction(
                    place, literals[ref.value]
                )
            elif isinstance(ref, AbsoluteRef):
                self.data[place : place + 4] = ref.gen_instruction(
                    place, sym_literals[ref.symbol_name]
                )
            elif isinstance(ref, Branch):
                linker.add_relocation(
                    section, start_offset + place, ref.symbol_name, ref.reloc_type
                )
            elif isinstance(ref, LocalBranch):
                target = self.labels[ref.label]
                assert target is not None
                self.data[place : place + 2] = ref.gen_instruction(place, target)

        for name, place in self.symbols.items():
            linker.add_symbol(
                name, start_offset + place, section, sym_type=SYM_TYPE_THUMB
            )

        for place, (sym_name, reloc_type) in self.extra_relocations.items():
            linker.add_relocation(section, start_offset + place, sym_name, reloc_type)

        if len(section.data) < (start_offset + len(self.data)):
            n = (start_offset + len(self.data)) - len(section.data)
            section.data.extend(b"\0" * n)
        section.data[start_offset : start_offset + len(self.data)] = self.data

    def finalize(self, linker: Linker, section_name: str) -> Section:
        section = linker.add_section(
            section_name, bytearray(), section_type=SECTION_TYPE_ROM
        )
        self.finalize_to(linker, section, 0)
        return section

    def __len__(self) -> int:
        return len(self.data)
