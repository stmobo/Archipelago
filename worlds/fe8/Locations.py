from __future__ import annotations

from typing import Dict, List, Optional

from BaseClasses import CollectionState, Entrance, Item, Location, MultiWorld, Region

from .fe8py.constants.characters import (
    CHAPTER_EXIT_REQUIREMENTS,
    CHAPTER_LINKS,
    CHAPTER_NAMES,
    CHAPTER_SHORT_NAMES,
    COMMON_CHAPTERS,
    EIRIKA,
    EIRIKA_CHAPTERS,
    EPHRAIM_CHAPTERS,
    RECRUITMENTS_BY_CHAPTER,
    SETH,
    CharacterFill,
    CharacterSlot,
    Recruitment,
)
from .fe8py.recruit_randomizer import CharacterAssignments
from .Items import FE8Item


class FE8Location(Location):
    game: str = "Fire Emblem The Sacred Stones"

    recruitment: Optional[Recruitment]
    char_slot: Optional[CharacterSlot]
    char_fill: Optional[CharacterFill]

    def __init__(
        self,
        player: int,
        name: str = "",
        code: Optional[int] = None,
        parent: Optional[Region] = None,
        *,
        recruitment: Optional[Recruitment],
        char_slot: Optional[CharacterSlot],
        char_fill: Optional[CharacterFill],
    ):
        super(FE8Location, self).__init__(player, name, code, parent)
        self.event = code is None
        self.recruitment = recruitment
        self.char_slot = char_slot
        self.char_fill = char_fill

        if self.char_slot is not None:
            print(f"created location for {char_slot.name} ({char_slot.id})")
        else:
            print(f"created empty location")


def create_region(
    world: MultiWorld, player: int, chapter_id: int, assignments: CharacterAssignments
) -> Region:
    region = Region(
        f"{CHAPTER_SHORT_NAMES[chapter_id]}: {CHAPTER_NAMES[chapter_id]}",
        player,
        world,
    )
    world.regions.append(region)

    print(f"Created region {region.name}")
    recruit_locations = []

    for recruitment in RECRUITMENTS_BY_CHAPTER.get(chapter_id, []):
        # Don't put locations down for Eirika and Seth.
        if recruitment.character_id == EIRIKA or recruitment.character_id == SETH:
            continue

        slot, fill = assignments.slot_char_id_lookup[recruitment.character_id]
        location = FE8Location(
            player,
            f"Recruit {slot.name}",
            slot.ap_id,
            region,
            recruitment=recruitment,
            char_slot=slot,
            char_fill=fill,
        )
        region.locations.append(location)
        location.item_rule = recruit_location_item_rule(player, location)
        if recruitment.requirements is not None:
            location.access_rule = create_character_access_rule(
                player, recruitment.requirements, assignments
            )

    entrance = Entrance(player, f"Completed {CHAPTER_SHORT_NAMES[chapter_id]}", region)
    entrance.access_rule = create_chapter_exit_rule(
        player, assignments, CHAPTER_EXIT_REQUIREMENTS.get(chapter_id)
    )
    region.exits = [entrance]

    return region


def create_chapter_regions(
    world: MultiWorld,
    player: int,
    assignments: CharacterAssignments,
    eirika_route: bool,
) -> Dict[int, Region]:
    ch_regions: Dict[int, Region] = {}
    for chapter_id in COMMON_CHAPTERS:
        ch_regions[chapter_id] = create_region(world, player, chapter_id, assignments)

    route_chapters = EIRIKA_CHAPTERS if eirika_route else EPHRAIM_CHAPTERS
    for chapter_id in route_chapters:
        ch_regions[chapter_id] = create_region(world, player, chapter_id, assignments)

    for chapter_id, region in ch_regions.items():
        # Connect entrances between chapters
        if chapter_id == 0x09:
            # C8 (ID 0x09) links to either C9A (0x0A) or C9B (0x17) depending on route
            next_chapter = 0x0A if eirika_route else 0x17
        else:
            next_chapter = CHAPTER_LINKS[chapter_id]
        if next_chapter is not None:
            region.exits[0].connect(ch_regions[next_chapter])

    return ch_regions


def create_character_access_rule(
    player: int,
    slot_ids: List[int],
    assignments: CharacterAssignments,
    require_any: bool = False,
):
    fill_names = [
        assignments.slot_character_to_item_name(slot_id) for slot_id in slot_ids
    ]

    if len(fill_names) == 0:
        return lambda state: True

    if require_any:
        return lambda state: any(state.has(name, player) for name in fill_names)
    else:
        return lambda state: all(state.has(name, player) for name in fill_names)


def ensure_locations_checked(recruit_locations: List[FE8Location]):
    return lambda state: all(
        location in state.locations_checked for location in recruit_locations
    )


def create_chapter_exit_rule(
    player: int,
    assignments: CharacterAssignments,
    exit_requirements: Optional[List[int]],
):
    def x(state: CollectionState) -> bool:
        if exit_requirements is not None:
            for char_id in exit_requirements:
                fill_name = assignments.slot_character_to_item_name(char_id)
                if not state.has(fill_name, player):
                    return False
        return True

    return x


def recruit_location_item_rule(player: int, location: FE8Location):
    def x(item: Item) -> bool:
        # Make sure that FE8 characters that stay within the player's own world
        # don't get placed into recruitment locations other than their own.
        # (e.g. don't place the Ross AP item into Joshua's recruitment AP location)
        if item.player != player or (not isinstance(item, FE8Item)):
            return True

        if item.char_slot is None:
            return False

        return item.char_slot.id == location.char_slot.id

    return x
