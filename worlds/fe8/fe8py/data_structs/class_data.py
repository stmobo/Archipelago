from __future__ import annotations

import random
from typing import TYPE_CHECKING, Tuple

from ..rom_struct import ArrayField, Field, RomStruct, StructID, rom_struct

if TYPE_CHECKING:
    from ..rom import ROM


@rom_struct
class ClassData(RomStruct):
    rom: ROM
    class_id: int = StructID(
        index_size=1, base_address=0x08807164, struct_size=0x54, index_adjustment=-1
    )

    name_text_id: int = Field.u16(0x00)
    desc_text_id: int = Field.u16(0x02)
    promotion: int = Field.u8(0x05)

    base_hp: int = Field.i8(0x0B)
    base_pow: int = Field.i8(0x0C)
    base_skl: int = Field.i8(0x0D)
    base_spd: int = Field.i8(0x0E)
    base_def: int = Field.i8(0x0F)
    base_res: int = Field.i8(0x10)
    base_con: int = Field.i8(0x11)
    base_mov: int = Field.i8(0x12)

    max_hp: int = Field.i8(0x13)
    max_pow: int = Field.i8(0x14)
    max_skl: int = Field.i8(0x15)
    max_spd: int = Field.i8(0x16)
    max_def: int = Field.i8(0x17)
    max_res: int = Field.i8(0x18)
    max_con: int = Field.i8(0x19)

    growth_hp: int = Field.i8(0x1B)
    growth_pow: int = Field.i8(0x1C)
    growth_skl: int = Field.i8(0x1D)
    growth_spd: int = Field.i8(0x1E)
    growth_def: int = Field.i8(0x1F)
    growth_res: int = Field.i8(0x20)
    growth_lck: int = Field.i8(0x21)

    promotion_hp: int = Field.u8(0x22)
    promotion_pow: int = Field.u8(0x23)
    promotion_skl: int = Field.u8(0x24)
    promotion_spd: int = Field.u8(0x25)
    promotion_def: int = Field.u8(0x26)
    promotion_res: int = Field.u8(0x27)

    attributes: int = Field.u32(0x28)
    base_ranks: Tuple[int, ...] = ArrayField.u8(0x2C, 8)
    promote_classes: Tuple[ClassData, ...] = None

    def __post_init__(self, *args, **kwargs):
        promo_info = 0x0895DFA4 + (self.class_id * 2)
        promo_a = self.rom.read_int(promo_info, 1)
        promo_b = self.rom.read_int(promo_info + 1, 1)
        if (promo_a != 0) and (promo_b != 0):
            self.promote_classes = (
                self.rom.get_class(promo_a),
                self.rom.get_class(promo_b),
            )
        elif promo_a != 0:
            self.promote_classes = (self.rom.get_class(promo_a),)
        elif promo_b != 0:
            self.promote_classes = (self.rom.get_class(promo_b),)
        else:
            self.promote_classes = tuple()

    def __post_save__(self):
        self.rom.update_class(self)

    @property
    def name(self) -> str:
        return str(self.rom.get_message(self.name_text_id))

    @property
    def description(self) -> str:
        return str(self.rom.get_message(self.desc_text_id))

    @property
    def is_flying(self) -> bool:
        return (self.attributes & (0x03 << 11)) != 0

    def scale_growths(self, factor: float) -> ClassData:
        return self.evolve(
            growth_hp=min(round(self.growth_hp * factor), 127),
            growth_pow=min(round(self.growth_pow * factor), 127),
            growth_skl=min(round(self.growth_skl * factor), 127),
            growth_spd=min(round(self.growth_spd * factor), 127),
            growth_def=min(round(self.growth_def * factor), 127),
            growth_res=min(round(self.growth_res * factor), 127),
            growth_lck=min(round(self.growth_lck * factor), 127),
        )

    def __str__(self) -> str:
        return "Class({:02x} : {})".format(self.class_id, self.name)
