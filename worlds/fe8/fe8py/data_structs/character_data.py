from __future__ import annotations

import random
from typing import (TYPE_CHECKING, Dict, Iterator, List, Optional, Set, Tuple,
                    Union)

from .. import constants
from ..rom_struct import (ArrayField, Field, RomStruct, StructAddress,
                          StructID, rom_struct)

if TYPE_CHECKING:
    from ..rom import ROM
    from .class_data import ClassData
    from .item_data import ItemData


@rom_struct
class CharacterData(RomStruct):
    rom: ROM
    character_id: int = StructID(
        index_size=1, base_address=0x08803D64, struct_size=0x34, index_adjustment=-1
    )
    name_text_id: int = Field.u16(0x00)
    desc_text_id: int = Field.u16(0x02)
    default_class_id: int = Field.u8(0x05)
    portrait_id: int = Field.u16(0x06)
    mini_portrait: int = Field.u16(0x07)
    affinity: int = Field.u8(0x09)
    sort_order: int = Field.u8(0x0A)

    base_level: int = Field.i8(0x0B)
    base_hp: int = Field.i8(0x0C)
    base_pow: int = Field.i8(0x0D)
    base_skl: int = Field.i8(0x0E)
    base_spd: int = Field.i8(0x0F)
    base_def: int = Field.i8(0x10)
    base_res: int = Field.i8(0x11)
    base_lck: int = Field.i8(0x12)
    base_con: int = Field.i8(0x13)

    base_ranks: Tuple[int, ...] = ArrayField(0x14, 1, 8, False)

    growth_hp: int = Field.u8(0x1C)
    growth_pow: int = Field.u8(0x1D)
    growth_skl: int = Field.u8(0x1E)
    growth_spd: int = Field.u8(0x1F)
    growth_def: int = Field.u8(0x20)
    growth_res: int = Field.u8(0x21)
    growth_lck: int = Field.u8(0x22)

    attributes: int = Field.u32(0x28)

    def __post_save__(self):
        self.rom.update_character(self)

    @property
    def name(self) -> str:
        return str(self.rom.get_message(self.name_text_id))

    @property
    def description(self) -> str:
        return str(self.rom.get_message(self.desc_text_id))

    @property
    def default_class(self) -> ClassData:
        return self.rom.get_class(self.default_class_id)

    @property
    def is_lord(self) -> bool:
        return self.character_id in constants.characters.LORDS

    @property
    def is_female(self) -> bool:
        return self.character_id in constants.characters.FEMALES

    @property
    def is_playable(self) -> bool:
        return self.character_id in constants.characters.PLAYABLE_CHARACTERS

    @property
    def is_thief(self) -> bool:
        return self.character_id in constants.characters.THIEVES

    @property
    def is_special(self) -> bool:
        return self.character_id in constants.characters.SPECIAL_CHARACTERS

    @property
    def requires_range(self) -> bool:
        return self.character_id in constants.characters.REQUIRES_RANGE

    @property
    def requires_melee(self) -> bool:
        return self.character_id in constants.characters.REQUIRES_MELEE

    @property
    def requires_flying(self) -> bool:
        return self.character_id in constants.characters.REQUIRES_FLYING

    @property
    def requires_attacking(self) -> bool:
        return self.character_id in constants.characters.REQUIRES_ATTACKING

    @property
    def can_randomize(self) -> bool:
        return not (self.is_lord or self.is_special or self.is_thief)

    @property
    def can_melee_attack(self) -> bool:
        return any(
            self.can_wield_weapon_type(wep_type)
            for wep_type in constants.items.MELEE_ATTACK_TYPES
        )

    @property
    def can_ranged_attack(self) -> bool:
        return any(
            self.can_wield_weapon_type(wep_type)
            for wep_type in constants.items.RANGED_ATTACK_TYPES
        )

    @property
    def can_attack(self) -> bool:
        return any(
            self.can_wield_weapon_type(wep_type)
            for wep_type in constants.items.ATTACK_CAPABLE_TYPES
        )

    def can_wield_weapon_type(self, item_type: int) -> bool:
        return (item_type in constants.items.WIELDABLE_TYPES) and (
            self.base_ranks[item_type] > 0
        )

    def can_wield_weapon(self, item_data: ItemData) -> bool:
        if item_data.weapon_type not in constants.items.WIELDABLE_TYPES:
            return False

        cur_rank = min(
            self.base_ranks[item_data.weapon_type],
            self.default_class.base_ranks[item_data.weapon_type],
        )

        return (cur_rank > 0) and (cur_rank >= item_data.weapon_exp_required)

    def apply_promotion(self, new_class: ClassData, apply_stats: bool) -> CharacterData:
        if apply_stats:
            new_base_hp = self.base_hp + new_class.promotion_hp
            new_base_pow = self.base_pow + new_class.promotion_pow
            new_base_skl = self.base_skl + new_class.promotion_skl
            new_base_spd = self.base_spd + new_class.promotion_spd
            new_base_def = self.base_def + new_class.promotion_def
            new_base_res = self.base_res + new_class.promotion_res
        else:
            new_base_hp = self.base_hp
            new_base_pow = self.base_pow
            new_base_skl = self.base_skl
            new_base_spd = self.base_spd
            new_base_def = self.base_def
            new_base_res = self.base_res

        prev_class = self.default_class
        new_base_ranks = list(self.base_ranks)
        for i in range(8):
            new_base_ranks[i] -= prev_class.base_ranks[i]
            new_base_ranks[i] = min(
                new_base_ranks[i] + new_class.base_ranks[i],
                constants.items.WEAPON_RANK_S,
            )

        if prev_class.class_id == constants.classes.PUPIL and new_class.class_id in (
            constants.classes.SHAMAN,
            constants.classes.SHAMAN_F,
        ):
            new_base_ranks[constants.items.ITEM_TYPE_ANIMA] = 0

        return self.evolve(
            base_hp=new_base_hp,
            base_pow=new_base_pow,
            base_skl=new_base_skl,
            base_spd=new_base_spd,
            base_def=new_base_def,
            base_res=new_base_res,
            base_ranks=tuple(new_base_ranks),
            base_level=1,
            default_class_id=new_class.class_id,
        )

    def apply_demotion(self, new_class: ClassData, apply_stats: bool) -> CharacterData:
        prev_class = self.default_class
        if apply_stats:
            new_base_hp = self.base_hp - prev_class.promotion_hp
            new_base_pow = self.base_pow - prev_class.promotion_pow
            new_base_skl = self.base_skl - prev_class.promotion_skl
            new_base_spd = self.base_spd - prev_class.promotion_spd
            new_base_def = self.base_def - prev_class.promotion_def
            new_base_res = self.base_res - prev_class.promotion_res
        else:
            new_base_hp = self.base_hp
            new_base_pow = self.base_pow
            new_base_skl = self.base_skl
            new_base_spd = self.base_spd
            new_base_def = self.base_def
            new_base_res = self.base_res

        new_base_ranks = list(self.base_ranks)
        for i in range(8):
            new_base_ranks[i] -= prev_class.base_ranks[i]
            new_base_ranks[i] = min(
                new_base_ranks[i] + new_class.base_ranks[i],
                constants.items.WEAPON_RANK_S,
            )

        if (
            prev_class.class_id
            in (constants.classes.SHAMAN, constants.classes.SHAMAN_F)
            and prev_class.class_id == constants.classes.PUPIL
        ):
            new_base_ranks[constants.items.ITEM_TYPE_ANIMA] = max(
                new_class.base_ranks[constants.items.ITEM_TYPE_ANIMA], 1
            )

        return self.evolve(
            base_hp=new_base_hp,
            base_pow=new_base_pow,
            base_skl=new_base_skl,
            base_spd=new_base_spd,
            base_def=new_base_def,
            base_res=new_base_res,
            base_ranks=tuple(new_base_ranks),
            base_level=1,
            default_class_id=new_class.class_id,
        )

    def apply_autolevel_scaling(
        self, n_levels: int, rng: random.Random, use_class_growths: bool = False
    ) -> CharacterData:
        if n_levels == 0:
            return self
        elif n_levels < 0:
            iters = -n_levels
        else:
            iters = n_levels

        new_base_hp = self.base_hp
        new_base_pow = self.base_pow
        new_base_skl = self.base_skl
        new_base_spd = self.base_spd
        new_base_def = self.base_def
        new_base_res = self.base_res
        new_base_lck = self.base_lck

        def random_point(grow_pct):
            nonlocal n_levels
            if rng.randint(0, 99) < grow_pct:
                if n_levels > 0:
                    return 1
                else:
                    return -1
            else:
                return 0

        for _ in range(iters):
            new_base_hp += random_point(
                self.growth_hp
                if not use_class_growths
                else self.default_class.growth_hp
            )
            new_base_pow += random_point(
                self.growth_pow
                if not use_class_growths
                else self.default_class.growth_pow
            )
            new_base_skl += random_point(
                self.growth_skl
                if not use_class_growths
                else self.default_class.growth_skl
            )
            new_base_spd += random_point(
                self.growth_spd
                if not use_class_growths
                else self.default_class.growth_spd
            )
            new_base_def += random_point(
                self.growth_def
                if not use_class_growths
                else self.default_class.growth_def
            )
            new_base_res += random_point(
                self.growth_res
                if not use_class_growths
                else self.default_class.growth_res
            )
            new_base_lck += random_point(
                self.growth_lck
                if not use_class_growths
                else self.default_class.growth_lck
            )

        return self.evolve(
            base_hp=new_base_hp,
            base_pow=new_base_pow,
            base_skl=new_base_skl,
            base_spd=new_base_spd,
            base_def=new_base_def,
            base_res=new_base_res,
            base_lck=new_base_lck,
        )

    @property
    def effective_hp(self) -> int:
        return self.base_hp + self.default_class.base_hp

    @property
    def effective_pow(self) -> int:
        return self.base_pow + self.default_class.base_pow

    @property
    def effective_skl(self) -> int:
        return self.base_skl + self.default_class.base_skl

    @property
    def effective_spd(self) -> int:
        return self.base_spd + self.default_class.base_spd

    @property
    def effective_def(self) -> int:
        return self.base_def + self.default_class.base_def

    @property
    def effective_res(self) -> int:
        return self.base_res + self.default_class.base_res

    @property
    def effective_con(self) -> int:
        return self.base_con + self.default_class.base_con

    def validate_stats(self):
        effective_hp = min(
            self.default_class.max_hp,
            max(10, self.base_hp + self.default_class.base_hp),
        )
        effective_pow = min(
            self.default_class.max_pow,
            max(0, self.base_pow + self.default_class.base_pow),
        )
        effective_skl = min(
            self.default_class.max_skl,
            max(0, self.base_skl + self.default_class.base_skl),
        )
        effective_spd = min(
            self.default_class.max_spd,
            max(0, self.base_spd + self.default_class.base_spd),
        )
        effective_def = min(
            self.default_class.max_def,
            max(0, self.base_def + self.default_class.base_def),
        )
        effective_res = min(
            self.default_class.max_res,
            max(0, self.base_res + self.default_class.base_res),
        )
        effective_con = min(
            self.default_class.max_con,
            max(0, self.base_con + self.default_class.base_con),
        )

        return self.evolve(
            base_hp=effective_hp - self.default_class.base_hp,
            base_pow=effective_pow - self.default_class.base_pow,
            base_skl=effective_skl - self.default_class.base_skl,
            base_spd=effective_spd - self.default_class.base_spd,
            base_def=effective_def - self.default_class.base_def,
            base_res=effective_res - self.default_class.base_res,
            base_lck=max(0, self.base_lck),
            base_con=effective_con - self.default_class.base_con,
        )

    @staticmethod
    def _redistribute_parameters(
        fill_params: List[int], slot_params: List[int]
    ) -> List[int]:
        ret = list(slot_params)
        fill_spread = sorted(range(len(fill_params)), key=lambda i: fill_params[i])
        slot_params = sorted(slot_params)
        for fill_idx, slot_val in zip(fill_spread, slot_params):
            ret[fill_idx] = slot_val
        return ret

    def redistribute_bases(
        self,
        prev_class: ClassData,
        new_class: ClassData,
        other: CharacterData,
        other_class: ClassData,
    ) -> CharacterData:
        new_bases = CharacterData._redistribute_parameters(
            [
                other.base_hp + other_class.base_hp,
                other.base_pow + other_class.base_pow,
                other.base_skl + other_class.base_skl,
                other.base_spd + other_class.base_spd,
                other.base_def + other_class.base_def,
                other.base_res + other_class.base_res,
                other.base_lck,
                other.base_con + other_class.base_con,
            ],
            [
                self.base_hp + prev_class.base_hp,
                self.base_pow + prev_class.base_pow,
                self.base_skl + prev_class.base_skl,
                self.base_spd + prev_class.base_spd,
                self.base_def + prev_class.base_def,
                self.base_res + prev_class.base_res,
                self.base_lck,
                self.base_con + prev_class.base_con,
            ],
        )

        return self.evolve(
            base_hp=new_bases[0] - new_class.base_hp,
            base_pow=new_bases[1] - new_class.base_pow,
            base_skl=new_bases[2] - new_class.base_skl,
            base_spd=new_bases[3] - new_class.base_spd,
            base_def=new_bases[4] - new_class.base_def,
            base_res=new_bases[5] - new_class.base_res,
            base_lck=new_bases[6],
            base_con=new_bases[7] - new_class.base_con,
        )

    def redistribute_growths(
        self,
        other: CharacterData,
    ) -> CharacterData:
        new_growths = CharacterData._redistribute_parameters(
            [
                other.growth_hp,
                other.growth_pow,
                other.growth_skl,
                other.growth_spd,
                other.growth_def,
                other.growth_res,
                other.growth_lck,
            ],
            [
                self.growth_hp,
                self.growth_pow,
                self.growth_skl,
                self.growth_spd,
                self.growth_def,
                self.growth_res,
                self.growth_lck,
            ],
        )

        return self.evolve(
            growth_hp=new_growths[0],
            growth_pow=new_growths[1],
            growth_skl=new_growths[2],
            growth_spd=new_growths[3],
            growth_def=new_growths[4],
            growth_res=new_growths[5],
            growth_lck=new_growths[6],
        )

    def fill_with(self, other: CharacterData, copy_stats: bool) -> CharacterData:
        kwargs = {
            "desc_text_id": other.desc_text_id,
            "default_class_id": other.default_class_id,
            "portrait_id": other.portrait_id,
            "mini_portrait": other.mini_portrait,
            "affinity": other.affinity,
            "sort_order": other.sort_order,
            "base_level": other.base_level,
            "base_ranks": list(other.base_ranks),
        }

        if copy_stats:
            kwargs["base_hp"] = other.base_hp
            kwargs["base_pow"] = other.base_pow
            kwargs["base_skl"] = other.base_skl
            kwargs["base_spd"] = other.base_spd
            kwargs["base_def"] = other.base_def
            kwargs["base_res"] = other.base_res
            kwargs["base_lck"] = other.base_lck
            kwargs["base_con"] = other.base_con

            kwargs["growth_hp"] = other.growth_hp
            kwargs["growth_pow"] = other.growth_pow
            kwargs["growth_skl"] = other.growth_skl
            kwargs["growth_spd"] = other.growth_spd
            kwargs["growth_def"] = other.growth_def
            kwargs["growth_res"] = other.growth_res
            kwargs["growth_lck"] = other.growth_lck

        return self.evolve(**kwargs)

    def __str__(self) -> str:
        return "Character({:02x} : {})".format(self.character_id, self.name)


# base table address for death quotes is 0x089ECD4C and has 79 entries
# base table symbol name is "gUnknown_089ECD4C"
@rom_struct
class CharacterDeathQuote(RomStruct):
    rom: ROM
    quote_addr: int = StructAddress()
    character_id: int = Field.u16(0x00)
    route: int = Field.u8(0x02)
    chapter_id: int = Field.u8(0x03)
    completion_event: int = Field.u16(0x04)
    text_id: int = Field.u16(0x06)
    unk: int = Field.u32(0x08)

    @property
    def character(self) -> CharacterData:
        return self.rom.get_character(self.character_id)
