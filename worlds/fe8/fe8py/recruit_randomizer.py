import random
from typing import Callable, Dict, Iterator, List, Tuple

from .constants.characters import (PLAYABLE_CHARACTERS, CharacterFill,
                                   CharacterSlot)


class CharacterPool:
    fills: Dict[int, CharacterFill]
    slots: Dict[int, CharacterSlot]
    assigned_ids: Dict[int, int]
    unrandomizable: List[Tuple[CharacterSlot, CharacterFill]]
    rng: random.Random
    assign_by_gender: bool

    def __init__(self, rng: random.Random, assign_by_gender: bool):
        self.rng = rng
        self.slots = {}
        self.fills = {}
        self.assigned_ids = {}
        self.unrandomizable = []
        self.assign_by_gender = assign_by_gender

        for id in PLAYABLE_CHARACTERS:
            slot = CharacterSlot.from_id(id)
            fill = CharacterFill.from_id(id)
            if slot.randomizable and fill.randomizable:
                self.slots[id] = slot
                self.fills[id] = fill
            else:
                self.unrandomizable.append((slot, fill))

    def _assign_internal(
        self,
        slot_filter: Callable[[CharacterSlot], bool],
        fill_filter: Callable[[CharacterFill], bool],
    ):
        slot_ids = [
            id
            for (id, slot) in self.slots.items()
            if (id not in self.assigned_ids) and slot_filter(slot)
        ]
        fill_ids = [
            id
            for (id, fill) in self.fills.items()
            if (id not in self.assigned_ids.values()) and fill_filter(fill)
        ]
        self.rng.shuffle(slot_ids)
        self.rng.shuffle(fill_ids)
        self.assigned_ids.update(zip(slot_ids, fill_ids))

    def assign(
        self,
        slot_filter: Callable[[CharacterSlot], bool],
        fill_filter: Callable[[CharacterFill], bool],
    ):
        if self.assign_by_gender:
            for rand_gender in (False, True):
                self._assign_internal(
                    lambda c: slot_filter(c) and (c.is_female == rand_gender),
                    lambda c: fill_filter(c) and (c.is_female == rand_gender),
                )
        else:
            self._assign_internal(slot_filter, fill_filter)

    def iter_randomized(self) -> Iterator[Tuple[CharacterSlot, CharacterFill]]:
        for slot_id, fill_id in self.assigned_ids.items():
            yield (self.slots[slot_id], self.fills[fill_id])

    def iter_all(self) -> Iterator[Tuple[CharacterSlot, CharacterFill]]:
        yield from self.unrandomizable
        yield from self.iter_randomized()


class CharacterAssignments:
    pool: CharacterPool
    fill_name_lookup: Dict[str, Tuple[CharacterSlot, CharacterFill]]
    slot_ap_id_lookup: Dict[int, Tuple[CharacterSlot, CharacterFill]]
    slot_char_id_lookup: Dict[int, Tuple[CharacterSlot, CharacterFill]]

    def __init__(self, pool: CharacterPool):
        self.pool = pool
        self.fill_name_lookup = {}
        self.slot_ap_id_lookup = {}
        self.slot_char_id_lookup = {}

        for (slot, fill) in pool.iter_all():
            # Items are named according to fill character, but use the ID of their assigned slot.
            self.slot_ap_id_lookup[slot.ap_id] = (slot, fill)
            self.slot_char_id_lookup[slot.id] = (slot, fill)
            self.fill_name_lookup[fill.name] = (slot, fill)

    def item_name_to_id(self, item_name: str) -> int:
        return self.fill_name_lookup[item_name][0].ap_id

    def item_id_to_name(self, item_id: int) -> str:
        return self.slot_ap_id_lookup[item_id][1].name

    def slot_character_to_item_name(self, slot_id: int) -> str:
        return self.slot_char_id_lookup[slot_id][1].name


def randomize_recruit_order(
    rng: random.Random, by_gender: bool
) -> CharacterAssignments:
    pool = CharacterPool(rng, by_gender)

    pool.assign(
        lambda char: char.requires_flying,
        lambda char: char.flying,
    )

    pool.assign(
        lambda char: char.requires_melee,
        lambda char: char.melee_capable,
    )

    pool.assign(
        lambda char: char.requires_range,
        lambda char: char.ranged_capable,
    )

    pool.assign(
        lambda char: char.requires_attack,
        lambda char: char.attack_capable,
    )

    pool.assign(
        lambda _: True,
        lambda _: True,
    )

    return CharacterAssignments(pool)
