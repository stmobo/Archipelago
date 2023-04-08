from __future__ import annotations

from functools import partial
from typing import Callable, Optional

# Maps from (data, place offset) -> field value (in relocation units)
FieldGetter = Callable[[bytes, int], int]

# Maps from (data, place offset, field value in relocation units) -> new bytes to write
FieldSetter = Callable[[bytes, int, int], bytes]


class RelocationOutOfRange(Exception):
    def __init__(self, value: int, reloc_type: Optional[str], *args: object) -> None:
        self.value = value
        self.reloc_type = reloc_type
        super().__init__(*args)

    def __str__(self) -> str:
        if self.reloc_type is None:
            return "Offset {:+x} out of range for relocation".format(self.value)
        return "Offset {:+x} out of range for {} relocation".format(
            self.value, self.reloc_type
        )


def raw_value_getter(place_size: int) -> FieldGetter:
    return lambda data, offset: int.from_bytes(
        data[offset : offset + place_size], "little", signed=False
    )


def raw_value_setter(place_size: int) -> FieldSetter:
    return lambda _data, _offset, value: value.to_bytes(
        place_size, "little", signed=False
    )


def bitfield_getter(
    place_size: int, start_bit: int, end_bit: int, signed: bool
) -> FieldGetter:
    return partial(
        get_bitfield,
        place_size=place_size,
        start_bit=start_bit,
        end_bit=end_bit,
        signed=signed,
    )


def bitfield_setter(
    place_size: int, start_bit: int, end_bit: int, signed: bool
) -> FieldSetter:
    return partial(
        set_bitfield,
        place_size=place_size,
        start_bit=start_bit,
        end_bit=end_bit,
        signed=signed,
    )


def get_bitfield(
    data: bytes,
    offset: int,
    *,
    place_size: int,
    start_bit: int,
    end_bit: int,
    signed: bool,
) -> int:
    place = int.from_bytes(data[offset : offset + place_size], "little", signed=False)
    field_size = end_bit - start_bit
    mask = (1 << field_size) - 1

    field_val = (place >> start_bit) & mask
    if signed and ((field_val & (1 << (field_size - 1))) != 0):
        return field_val - (1 << field_size)
    return field_val


def set_bitfield(
    data: bytes,
    offset: int,
    value: int,
    *,
    place_size: int,
    start_bit: int,
    end_bit: int,
    signed: bool,
) -> bytes:
    field_size = end_bit - start_bit
    mask = (1 << field_size) - 1

    if value < 0:
        if signed:
            value = (value + (1 << field_size)) | (1 << (field_size - 1))
        else:
            raise ValueError("Bitfield value cannot be negative")

    if (value & ~mask) != 0:
        raise RelocationOutOfRange(value, str(field_size) + "-bit")

    place = int.from_bytes(data[offset : offset + place_size], "little", signed=False)
    place = (place & ~(mask << start_bit)) | (value << start_bit)
    return place.to_bytes(place_size, "little", signed=False)


def _get_arm_pc13(data: bytes, offset: int) -> int:
    place = int.from_bytes(data[offset : offset + 4], "little", signed=False)
    value = place & 0x0FFF
    if (place & (1 << 23)) == 0:
        return -value
    return value


def _set_arm_pc13(data: bytes, offset: int, value: int) -> bytes:
    place = int.from_bytes(data[offset : offset + 4], "little", signed=False)
    place = place & ~0x00800FFF

    if value < -0x0FFF or value > 0x0FFF:
        raise RelocationOutOfRange(value, "ARM_PC13")

    if value < 0:
        place |= (1 << 23) | (-value & 0x0FFF)
    else:
        place |= value & 0x0FFF

    return place.to_bytes(4, "little", signed=False)


def _get_thumb_pc22(data: bytes, offset: int) -> int:
    field1 = get_bitfield(
        data, offset, place_size=2, start_bit=0, end_bit=11, signed=False
    )
    field2 = get_bitfield(
        data, offset + 2, place_size=2, start_bit=0, end_bit=11, signed=False
    )

    val = (field1 << 11) | field2
    if (val & (1 << 21)) != 0:
        return val - (1 << 22)
    return val


def _set_thumb_pc22(data: bytes, offset: int, value: int) -> bytes:
    if (value >= (1 << 22)) or (value <= -(1 << 22)):
        raise RelocationOutOfRange(value, "THM_PC22")

    value1 = value & 0x07FF
    value2 = (value >> 11) & 0x07FF

    field1 = set_bitfield(
        data, offset, value2, place_size=2, start_bit=0, end_bit=11, signed=False
    )
    field2 = set_bitfield(
        data, offset + 2, value1, place_size=2, start_bit=0, end_bit=11, signed=False
    )
    return field1 + field2


def _get_thumb_pc8(data: bytes, offset: int) -> int:
    value = get_bitfield(
        data, offset, place_size=2, start_bit=0, end_bit=8, signed=False
    )
    if value == 255:
        return -1
    return value


def _set_thumb_pc8(data: bytes, offset: int, value: int) -> bytes:
    if (value < -1) or (value > 254):
        raise RelocationOutOfRange(value, "THM_PC8")
    if value == -1:
        value = 255
    return set_bitfield(
        data, offset, value, place_size=2, start_bit=0, end_bit=8, signed=False
    )


class RelocationType:
    name: str
    place_relative: bool
    ignore_field: bool
    set_thumb_bit: bool
    unit_size: int
    field_getter: FieldGetter
    field_setter: FieldSetter
    veneer_type: Optional[str]

    def __init__(
        self,
        name: str,
        place_relative: bool,
        unit_size: int,
        field_getter: FieldGetter,
        field_setter: FieldSetter,
        *,
        ignore_field: bool = False,
        set_thumb_bit: bool = False,
        veneer_type: Optional[str] = None,
    ) -> None:
        self.name = name
        self.place_relative = place_relative
        self.ignore_field = ignore_field
        self.set_thumb_bit = set_thumb_bit
        self.unit_size = unit_size
        self.field_getter = field_getter
        self.field_setter = field_setter
        self.veneer_type = veneer_type

    def calculate_field_value(
        self,
        data: bytes,
        offset: int,
        base_addr: int,
        sym_value: int,
        addend: int,
        override_field: Optional[int],
    ):
        place = offset + base_addr

        if not self.ignore_field:
            if override_field is not None:
                addend += override_field * self.unit_size
            else:
                addend += self.field_getter(data, offset) * self.unit_size

        if self.place_relative:
            write_val = sym_value - place + addend
        else:
            write_val = sym_value + addend

        return write_val // self.unit_size

    def get_original_field(
        self,
        data: bytes,
        place: int,
        base_addr: int,
        sym_value: int,
        sym_base: int,
        addend: int,
    ) -> bytes:
        if self.ignore_field:
            return 0

        field = self.field_getter(data, place - base_addr)
        if self.set_thumb_bit:
            field &= ~1

        field *= self.unit_size
        if self.place_relative:
            field += place - sym_value
        else:
            field -= sym_value

        field -= sym_base
        field -= addend
        return field // self.unit_size

    def __call__(
        self,
        data: bytes,
        offset: int,
        base_addr: int,
        sym_value: int,
        addend: int,
        sym_type: int,
        override_field: Optional[int],
    ) -> bytes:
        write_val = self.calculate_field_value(
            data, offset, base_addr, sym_value, addend, override_field
        )
        if self.set_thumb_bit:
            if sym_type == 3:  # Thumb
                write_val |= 1
            elif sym_type == 2:  # ARM
                write_val &= ~1
        return self.field_setter(data, offset, write_val)


# These two aren't part of the ELF standard, but are useful for our purposes
OVERWRITE_32 = RelocationType(
    "OVERWRITE_32",
    False,
    1,
    raw_value_getter(4),
    raw_value_setter(4),
    ignore_field=True,
    set_thumb_bit=True,
)
OVERWRITE_16 = RelocationType(
    "OVERWRITE_16",
    False,
    1,
    raw_value_getter(2),
    raw_value_setter(2),
    ignore_field=True,
    set_thumb_bit=True,
)

DATA_32 = RelocationType(
    "DATA_32",
    False,
    1,
    raw_value_getter(4),
    raw_value_setter(4),
    ignore_field=True,
    set_thumb_bit=False,
)

ABSOLUTE_32 = RelocationType(
    "ARM_ABS32", False, 1, raw_value_getter(4), raw_value_setter(4), set_thumb_bit=True
)
RELATIVE_32 = RelocationType(
    "ARM_REL32", True, 1, raw_value_getter(4), raw_value_setter(4), set_thumb_bit=True
)
ABSOLUTE_16 = RelocationType(
    "ARM_ABS16", False, 1, raw_value_getter(2), raw_value_setter(2), set_thumb_bit=True
)
ABSOLUTE_8 = RelocationType(
    "ARM_ABS8", False, 1, raw_value_getter(1), raw_value_setter(1), set_thumb_bit=True
)

THM_PC22 = THM_CALL = R_ARM_THM_CALL = RelocationType(
    "THM_PC22", True, 2, _get_thumb_pc22, _set_thumb_pc22, veneer_type="thumb"
)

THM_JUMP11 = R_ARM_THM_JUMP11 = RelocationType(
    "THM_JUMP11",
    True,
    2,
    bitfield_getter(2, 0, 11, True),
    bitfield_setter(2, 0, 11, True),
    veneer_type="thumb",
)

THM_JUMP8 = R_ARM_THM_JUMP8 = RelocationType(
    "THM_JUMP8",
    True,
    2,
    bitfield_getter(2, 0, 8, True),
    bitfield_setter(2, 0, 8, True),
    veneer_type="thumb",
)

# Table of standard ELF relocation types for ARM:
RELOCATION_TYPES = {
    1: RelocationType(
        "ARM_PC24",
        True,
        4,
        bitfield_getter(4, 0, 24, True),
        bitfield_setter(4, 0, 24, True),
        veneer_type="arm",
    ),
    2: ABSOLUTE_32,
    3: RELATIVE_32,
    4: RelocationType(
        "ARM_PC13", True, 1, _get_arm_pc13, _set_arm_pc13, veneer_type="arm"
    ),
    5: ABSOLUTE_16,
    6: RelocationType(
        "ARM_ABS12",
        False,
        1,
        bitfield_getter(4, 0, 12, False),
        bitfield_setter(4, 0, 12, False),
        veneer_type="arm",
    ),
    7: RelocationType(
        "THM_ABS5",
        False,
        4,
        bitfield_getter(2, 6, 11, False),
        bitfield_setter(2, 6, 11, False),
        veneer_type="thumb",
    ),
    8: ABSOLUTE_8,
    10: THM_PC22,
    11: RelocationType(
        "THM_PC8", True, 4, _get_thumb_pc8, _set_thumb_pc8, veneer_type="thumb"
    ),
    102: R_ARM_THM_JUMP11,
    103: R_ARM_THM_JUMP8,
}
