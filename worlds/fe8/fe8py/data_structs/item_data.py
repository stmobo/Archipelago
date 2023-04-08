from __future__ import annotations

import random
from typing import TYPE_CHECKING

from ..constants import items
from ..rom_struct import Field, PointerField, RomStruct, StructID, rom_struct

if TYPE_CHECKING:
    from ..rom import ROM


@rom_struct
class ItemData(RomStruct):
    rom: ROM
    item_id: int = StructID(
        index_size=1, base_address=0x08809B10, struct_size=0x24, index_adjustment=0
    )

    name_text_id: int = Field.u16(0x00)
    desc_text_id: int = Field.u16(0x02)
    use_desc_text_id: int = Field.u16(0x04)

    weapon_type: int = Field.u8(0x07)
    attributes: int = Field.u32(0x08)

    stat_bonus_ptr: int = PointerField(0x0C)
    effectiveness_ptr: int = PointerField(0x10)

    max_uses: int = Field.u8(0x14)

    might: int = Field.u8(0x15)
    hit: int = Field.u8(0x16)
    weight: int = Field.u8(0x17)
    crit: int = Field.u8(0x18)

    encoded_range: int = Field.u8(0x19)

    cost_per_use: int = Field.u16(0x1A)
    weapon_exp_required: int = Field.u8(0x1C)
    icon_id: int = Field.u8(0x1D)
    use_effect_id: int = Field.u8(0x1E)
    weapon_effect_id: int = Field.u8(0x1F)
    weapon_exp_awarded: int = Field.u8(0x20)

    # attribute bits:
    # bit 0:  item is weapon
    # bit 18: item is locked to Eirika (i.e. Sieglinde)
    # bit 19: item is locked to Ephraim (i.e. Reginleif)

    def __post_save__(self):
        self.rom.update_item(self)

    @property
    def name(self) -> str:
        return str(self.rom.get_message(self.name_text_id))

    @property
    def description(self) -> str:
        return str(self.rom.get_message(self.desc_text_id))

    @property
    def use_description(self) -> str:
        return str(self.rom.get_message(self.use_desc_text_id))

    @property
    def is_wieldable(self) -> bool:
        return (self.item_id not in items.UNUSABLE_ITEMS) and (
            self.item_id in items.WIELDABLE_TYPES
        )

    @property
    def is_randomizable_consumable(self) -> bool:
        return self.item_id in items.RANDOMIZABLE_CONSUMABLES

    @property
    def is_stat_booster(self) -> bool:
        return self.item_id in items.STAT_BOOSTERS

    def __str__(self) -> str:
        return "Item({:02x} : {})".format(self.item_id, self.name)
