from __future__ import annotations

from typing import Optional

from BaseClasses import Item, ItemClassification

from .fe8py.constants.characters import AP_ID_OFFSET, CharacterFill, CharacterSlot


class FE8Item(Item):
    game: str = "Fire Emblem The Sacred Stones"

    char_slot: Optional[CharacterSlot]
    char_fill: Optional[CharacterFill]

    def __init__(
        self,
        name: str,
        classification: ItemClassification,
        code: Optional[int],
        player: int,
        *,
        char_slot: Optional[CharacterSlot],
        char_fill: Optional[CharacterFill]
    ):
        super(FE8Item, self).__init__(name, classification, code, player)
        self.char_slot = char_slot
        self.char_fill = char_fill

    @classmethod
    def from_character_assignment(
        cls, player: int, slot: CharacterSlot, fill: CharacterFill
    ) -> FE8Item:
        return cls(
            fill.name,
            ItemClassification.progression,
            slot.ap_id,
            player,
            char_slot=slot,
            char_fill=fill,
        )

    @classmethod
    def create_event(cls, player: int, event: str) -> FE8Item:
        return cls(
            event,
            ItemClassification.progression,
            None,
            player,
            char_slot=None,
            char_fill=None,
        )

    @classmethod
    def create_dummy(
        cls,
        player: int,
        name: str,
        id_offset: int,
    ) -> FE8Item:
        return cls(
            name,
            ItemClassification.filler,
            AP_ID_OFFSET + id_offset,
            player,
            char_slot=None,
            char_fill=None,
        )
