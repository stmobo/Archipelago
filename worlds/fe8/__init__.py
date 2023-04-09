from __future__ import annotations

import json
import os.path as osp
from typing import Dict

from BaseClasses import Entrance, Item, ItemClassification, Location, MultiWorld, Region

from ..AutoWorld import WebWorld, World
from .fe8py.constants.characters import (
    AP_ITEM_NAMES_TO_IDS,
    AP_LOCATION_NAMES_TO_IDS,
    EIRIKA,
    EPHRAIM,
    SETH,
)
from .fe8py.local_patcher import PatcherCharacterData, PatcherData, PatcherItemData
from .fe8py.recruit_randomizer import CharacterAssignments, randomize_recruit_order
from .Items import FE8Item
from .Locations import FE8Location, create_chapter_regions
from .Options import fe8_options


class FE8World(World):
    """
    TODO: fill in
    """

    option_definitions = fe8_options
    game = "Fire Emblem The Sacred Stones"
    topology_present = False
    data_version = 1

    item_name_to_id = AP_ITEM_NAMES_TO_IDS
    location_name_to_id = AP_LOCATION_NAMES_TO_IDS

    character_assignments: CharacterAssignments
    eirika_route: bool
    chapter_regions: Dict[int, Region]
    character_recruit_locations: Dict[int, FE8Location]  # slot character ID to Location
    character_items: Dict[int, FE8Item]  # slot character ID to Item

    def generate_early(self):
        randomized_recruitment = get_options(
            self.multiworld, "randomized_recruitment", self.player
        )

        if randomized_recruitment:
            self.character_assignments = randomize_recruit_order(
                self.multiworld.random,
                get_options(
                    self.multiworld, "disable_crossgender_recruitment", self.player
                ),
            )
        else:
            self.character_assignments = CharacterAssignments.identity_map()

        route = get_options(self.multiworld, "route", self.player)
        self.eirika_route = route == 0

        self.character_items = {}

        for slot, fill in self.character_assignments.pool.iter_all():
            item = FE8Item.from_character_assignment(self.player, slot, fill)
            self.character_items[slot.id] = item

        # Precollect Eirika as the lord for the prologue through C8.
        # Also precollect Seth, since Eirika's almost certainly not gonna get very far on her own.
        # (Also, there's no recruit event entry for Seth.)
        for char_id in [EIRIKA, SETH]:
            self.multiworld.push_precollected(self.character_items[char_id])

    def create_item(self, name: str) -> FE8Item:
        if name == "filler":
            return FE8Item.create_dummy(self.player, "filler", 0)
        else:
            slot = self.character_assignments.fill_name_lookup[name][0]
            return self.character_items[slot.id]

    def create_regions(self):
        menu_region = Region("Menu", self.player, self.multiworld)
        self.multiworld.regions += [menu_region]

        self.chapter_regions = create_chapter_regions(
            self.multiworld, self.player, self.character_assignments, self.eirika_route
        )

        # Get all character recruit locations:
        self.character_recruit_locations = {}
        for region in self.chapter_regions.values():
            for location in region.locations:
                if location.char_slot is not None:
                    assert location.char_slot.id not in self.character_recruit_locations
                    self.character_recruit_locations[location.char_slot.id] = location

        # Connect menu region to prologue
        start_entrance = Entrance(self.player, "Start Game", menu_region)
        menu_region.exits = [start_entrance]
        start_entrance.connect(self.chapter_regions[0])

        # Create final boss location
        final_region = Region("End", self.player, self.multiworld)
        final_region.locations.append(
            FE8Location(
                self.player,
                "Defeat Fomortiis",
                None,
                final_region,
                recruitment=None,
                char_slot=None,
                char_fill=None,
            )
        )
        self.multiworld.regions.append(final_region)

        # Connect final boss region
        if self.eirika_route:
            self.chapter_regions[0x16].exits[0].connect(final_region)
        else:
            self.chapter_regions[0x23].exits[0].connect(final_region)

    def create_items(self):
        exclude_items = set(
            item.name for item in self.multiworld.precollected_items[self.player]
        )

        for slot, fill in self.character_assignments.pool.iter_all():
            if slot.id == EIRIKA or slot.id == SETH:
                # Recruitment locations aren't created for Eirika and Seth;
                # don't make filler items for them.
                continue
            elif fill.name in exclude_items:
                self.multiworld.itempool.append(self.create_item("filler"))
            elif slot.id == EPHRAIM and not self.eirika_route:
                # If we're on Ephraim's route, lock him to his slot in C8 instead of adding him to the pool.
                self.character_recruit_locations[EPHRAIM].place_locked_item(
                    self.character_items[EPHRAIM]
                )
            else:
                self.multiworld.itempool.append(self.character_items[slot.id])

        print(len(self.multiworld.itempool))

    def generate_basic(self):
        self.multiworld.get_location("Defeat Fomortiis", self.player).place_locked_item(
            FE8Item.create_event(self.player, "Victory")
        )
        self.multiworld.completion_condition[self.player] = lambda state: state.has(
            "Victory", self.player
        )

    def generate_output(self, output_directory: str):
        starting_item_names = set(
            item.name for item in self.multiworld.precollected_items[self.player]
        )

        character_data = []
        for slot, fill in self.character_assignments.pool.iter_all():
            precollected = fill.name in starting_item_names
            char_item = self.character_items[slot.id]

            if slot.id in self.character_recruit_locations:
                src_player = char_item.location.player
                receive_item = PatcherItemData(
                    src_player,
                    self.multiworld.player_name[src_player],
                    char_item.code,
                    char_item.name,
                )

                recruit_loc = self.character_recruit_locations[slot.id]
                loc_id = recruit_loc.address
                send_item = PatcherItemData(
                    recruit_loc.item.player,
                    self.multiworld.player_name[recruit_loc.item.player],
                    recruit_loc.item.code,
                    recruit_loc.item.name,
                )
            else:
                receive_item = PatcherItemData(
                    self.player,
                    self.multiworld.player_name[self.player],
                    char_item.code,
                    char_item.name,
                )
                send_item = None
                loc_id = None

            character_data.append(
                PatcherCharacterData(
                    slot, fill, receive_item, send_item, loc_id, precollected
                )
            )

        death_link = get_options(self.multiworld, "death_link", self.player)
        patcher_data = PatcherData(
            self.multiworld.seed_name,
            self.multiworld.seed,
            self.player,
            self.multiworld.player_name[self.player],
            self.eirika_route,
            death_link,
            character_data,
        )

        out_name = f"AP-{self.multiworld.seed_name}-P{self.player}-{self.multiworld.get_file_safe_player_name(self.player)}.APFE8"
        with open(osp.join(output_directory, out_name), "w", encoding="utf-8") as f:
            json.dump(patcher_data.to_dict(), f)


def get_options(world: MultiWorld, name: str, player: int):
    return getattr(world, name, None)[player].value
