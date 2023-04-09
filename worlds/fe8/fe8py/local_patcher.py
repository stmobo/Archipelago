from __future__ import annotations

import random
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

from . import constants
from .constants.characters import CharacterFill, CharacterSlot
from .data_structs import CharacterData, CharacterDeathQuote, ItemData
from .event_patcher import EventPatches
from .linker import SECTION_TYPE_ROM, SYM_TYPE_DATA, Linker, relocation_types
from .rom import ROM
from .text import Message, inject_messages, replace_names

DEMOTE_TABLE: Dict[int, Set[int]] = {}


def _is_randomizable_item(item: Union[ItemData, int]) -> bool:
    try:
        item_id = item.item_id
    except AttributeError:
        item_id = item

    return (
        (item_id in constants.items.WEAPON_RANDOMIZER_CANDIDATES)
        or (item_id in constants.items.RANDOMIZABLE_CONSUMABLES)
        or (item_id in constants.items.STAT_BOOSTERS)
    )


def apply_slot_substitution(
    slot: CharacterData, fill: CharacterData, rng: random.Random
) -> CharacterData:
    should_promote = slot.default_class_id in constants.classes.PROMOTED_CLASSES
    is_promoted = fill.default_class_id in constants.classes.PROMOTED_CLASSES
    target_level = slot.base_level
    cur_level = fill.base_level

    if should_promote:
        target_level += 10

    if is_promoted:
        cur_level += 10

    promo_text = fill.default_class.name
    level_adjustment = target_level - cur_level

    new_data = slot.fill_with(fill, True)

    if should_promote and not is_promoted:
        level_adjustment -= 3

    # new_data.redistribute_stats(prev_slot_class, new_class, fill, prev_fill_class, False, False)

    if should_promote and not is_promoted:
        # randomly pick a class to promote to (if we can)
        prev_class = new_data.default_class
        if len(prev_class.promote_classes) > 0:
            new_class = rng.choice(prev_class.promote_classes)
            new_data = new_data.apply_promotion(new_class, True)
            promo_text = "{} (promoted from {})".format(new_class.name, prev_class.name)
    elif is_promoted and not should_promote:
        # randomly pick a base class to demote to (if we can)
        prev_class = new_data.default_class
        if prev_class.class_id in constants.classes.DEMOTIONS:
            valid_demotes = [
                new_data.rom.get_class(class_id)
                for class_id in constants.classes.DEMOTIONS[prev_class.class_id]
                if class_id not in constants.classes.TRAINEE_CLASSES
            ]
            new_class = rng.choice(valid_demotes)
            new_data = new_data.apply_demotion(new_class, True)
            promo_text = "{} (demoted from {})".format(new_class.name, prev_class.name)

    new_data = new_data.apply_autolevel_scaling(level_adjustment, rng)
    new_data = new_data.validate_stats()

    # new_data.base_ranks = [max(char_rank, class_rank) for (char_rank, class_rank) in zip(new_data.base_ranks, new_class.base_ranks)]

    print("\n[ {} => {} ]".format(fill.name, slot.name))
    print(
        "Level {} (effective change {:+d}) | Class: {}".format(
            new_data.base_level, level_adjustment, promo_text
        )
    )
    print("        MHP | M/S | Skl | Spd | Def | Res | Lck | Con")
    print(
        "Stats:  {:3d} | {:3d} | {:3d} | {:3d} | {:3d} | {:3d} | {:3d} | {:3d}".format(
            new_data.effective_hp,
            new_data.effective_pow,
            new_data.effective_skl,
            new_data.effective_spd,
            new_data.effective_def,
            new_data.effective_res,
            new_data.base_lck,
            new_data.effective_con,
        )
    )
    print(
        "D-Fill: {:+3d} | {:+3d} | {:+3d} | {:+3d} | {:+3d} | {:+3d} | {:+3d} | {:+3d}".format(
            new_data.effective_hp - fill.effective_hp,
            new_data.effective_pow - fill.effective_pow,
            new_data.effective_skl - fill.effective_skl,
            new_data.effective_spd - fill.effective_spd,
            new_data.effective_def - fill.effective_def,
            new_data.effective_res - fill.effective_res,
            new_data.base_lck - fill.base_lck,
            new_data.effective_con - fill.effective_con,
        )
    )
    print(
        "D-Slot: {:+3d} | {:+3d} | {:+3d} | {:+3d} | {:+3d} | {:+3d} | {:+3d} | {:+3d}".format(
            new_data.effective_hp - slot.effective_hp,
            new_data.effective_pow - slot.effective_pow,
            new_data.effective_skl - slot.effective_skl,
            new_data.effective_spd - slot.effective_spd,
            new_data.effective_def - slot.effective_def,
            new_data.effective_res - slot.effective_res,
            new_data.base_lck - slot.base_lck,
            new_data.effective_con - slot.effective_con,
        )
    )

    return new_data


class PatcherItemData:
    # For sent items in other worlds, these two properties are the ID and name of the destination player.
    # For received items (in this world), they are the ID and name of the player who will send the item to us.
    player_id: int
    player_name: str

    item_id: int
    item_name: str

    def __init__(self, player_id: int, player_name: str, item_id: int, item_name: str):
        self.player_id = player_id
        self.player_name = player_name
        self.item_id = item_id
        self.item_name = item_name

    def to_dict(self) -> dict:
        return {
            "player": self.player_id,
            "item": self.item_id,
            "player_name": self.player_name,
            "item_name": self.item_name,
        }

    @classmethod
    def from_dict(cls, src: dict) -> PatcherItemData:
        return cls(src["player"], src["player_name"], src["item"], src["item_name"])


class PatcherCharacterData:
    slot: CharacterSlot
    fill: CharacterFill
    receive_item: PatcherItemData  # Item we'll receive to unlock this character
    send_item: Optional[
        PatcherItemData
    ]  # Item we'll send once this character is recruited, if any
    location_id: Optional[int]  # ID of this character's recruitment location
    precollected: bool  # if True, this character is in our starting inventory

    def __init__(
        self,
        slot: CharacterSlot,
        fill: CharacterFill,
        receive_item: PatcherItemData,
        send_item: Optional[PatcherItemData],
        location_id: Optional[int],
        precollected: bool,
    ):
        self.slot = slot
        self.fill = fill
        self.receive_item = receive_item
        self.send_item = send_item
        self.location_id = location_id
        self.precollected = precollected

    def to_dict(self) -> dict:
        ret = {
            "slot": self.slot.id,
            "fill": self.fill.id,
            "precollected": self.precollected,
            "receive_item": self.receive_item.to_dict(),
        }

        if self.send_item is not None:
            ret["send_item"] = self.send_item.to_dict()

        if self.location_id is not None:
            ret["location_id"] = self.location_id

        return ret

    @classmethod
    def from_dict(cls, src: dict) -> PatcherCharacterData:
        if "send_item" in src:
            send_item = PatcherItemData.from_dict(src["send_item"])
        else:
            send_item = None

        return cls(
            CharacterFill.from_id(src["slot"]),
            CharacterFill.from_id(src["fill"]),
            PatcherItemData.from_dict(src["receive_item"]),
            send_item,
            src.get("location_id", None),
            src["precollected"],
        )


class PatcherData:
    seed_name: str
    seed: int
    player_id: int
    player_name: str
    eirika_route: bool
    death_link: bool
    characters: List[PatcherCharacterData]

    def __init__(
        self,
        seed_name: str,
        seed: int,
        player_id: int,
        player_name: str,
        eirika_route: bool,
        death_link: bool,
        characters: List[PatcherCharacterData],
    ):
        self.seed_name = seed_name
        self.seed = seed
        self.player_id = player_id
        self.player_name = player_name
        self.eirika_route = eirika_route
        self.death_link = death_link
        self.characters = characters

    def to_dict(self) -> dict:
        return {
            "seed_name": self.seed_name,
            "seed": self.seed,
            "player_name": self.player_name,
            "player_id": self.player_id,
            "eirika_route": self.eirika_route,
            "death_link": self.death_link,
            "characters": [data.to_dict() for data in self.characters],
        }

    @classmethod
    def from_dict(cls, src: dict) -> PatcherData:
        return cls(
            src["seed_name"],
            src["seed"],
            src["player_id"],
            src["player_name"],
            src["eirika_route"],
            src["death_link"],
            [PatcherCharacterData.from_dict(data) for data in src["characters"]],
        )


def patch_rom(base_rom: ROM, patch_data: PatcherData, connector_port: int) -> bytearray:
    new_rom = base_rom.clone(False)
    rng = random.Random(patch_data.seed)

    name_replacements: Dict[str, str] = {}
    portrait_replacements: Dict[int, int] = {}
    for char_data in patch_data.characters:
        slot = base_rom.get_character(char_data.slot.id)
        fill = base_rom.get_character(char_data.fill.id)

        name_replacements[slot.name] = fill.name
        try:
            slot_portraits = constants.characters.PORTRAIT_IDS[slot.character_id]
            fill_portraits = constants.characters.PORTRAIT_IDS[fill.character_id]
            for portrait in slot_portraits:
                portrait_replacements[portrait] = fill_portraits[0]
        except KeyError:
            pass

        apply_slot_substitution(slot, fill, rng).with_rom(new_rom).save()

    replace_names(new_rom.messages, name_replacements, portrait_replacements)

    all_given_items: List[ItemData] = []
    all_chest_items: List[ItemData] = []
    all_shop_items: List[ItemData] = []
    all_inv_consumables: List[ItemData] = []
    all_inv_stat_boosters: List[ItemData] = []

    all_enemy_class_ids: Set[int] = set()
    all_enemy_character_ids: Dict[int, Set[int]] = {}

    n_enemy_defs = 0

    i = 0
    for event_group in new_rom.load_map_events():
        for given_item in event_group.given_items:
            print(f"[{event_group.map_name}] found given item: {given_item.item.name}")
            if _is_randomizable_item(given_item.item):
                all_given_items.append(given_item.item)

        for chest in event_group.chests:
            if (chest.item is not None) and _is_randomizable_item(chest.item):
                all_chest_items.append(chest.item)

        for shop in event_group.shops:
            all_shop_items.extend(shop.iter_items())

        for unit_def in event_group.unit_definitions:
            if unit_def.character_id in constants.characters.PLAYABLE_CHARACTERS:
                for item_id in unit_def.items:
                    if item_id is None:
                        continue
                    if item_id in constants.items.RANDOMIZABLE_CONSUMABLES:
                        all_inv_consumables.append(new_rom.get_item(item_id))
                    if item_id in constants.items.STAT_BOOSTERS:
                        all_inv_stat_boosters.append(new_rom.get_item(item_id))
            elif unit_def.is_enemy:
                n_enemy_defs += 1
                all_enemy_class_ids.add(unit_def.class_id)
                all_enemy_character_ids.setdefault(unit_def.character_id, set()).add(i)
        i += 1

    print(f"Found {n_enemy_defs} enemy definitions.")

    for event_group in new_rom.load_map_events():
        given_items_modified = 0
        chests_modified = 0
        shops_modified = 0
        unit_defs_modified = 0
        chapter_enemy_defs = 0
        chapter_enemy_drops = 0

        for given_item in event_group.given_items:
            if _is_randomizable_item(given_item.item) and (len(all_given_items) > 0):
                replacement = all_given_items.pop()
                print(
                    "[{}] Replacing given {} with a {}".format(
                        event_group.map_name, given_item.item.name, replacement.name
                    )
                )
                given_item.with_item(replacement).save()
                given_items_modified += 1

        for chest in event_group.chests:
            if (
                (chest.item is not None)
                and _is_randomizable_item(chest.item)
                and (len(all_chest_items) > 0)
            ):
                chest.with_item(all_chest_items.pop()).save()
                chests_modified += 1

        for shop in event_group.shops:
            modified = False
            for i in range(len(shop.item_ids)):
                if len(all_shop_items) > 0:
                    shop.item_ids[i] = all_shop_items.pop().item_id
                    modified = True
            if modified:
                shop.save()
                shops_modified += 1

        unit_def_levels = []

        for unit_def in event_group.unit_definitions:
            if unit_def.is_enemy:
                chapter_enemy_defs += 1
                if (unit_def.props_2 & (1 << 13)) != 0:
                    chapter_enemy_drops += 1
                unit_def_levels.append(unit_def.level)

            inv = list(unit_def.items)
            new_character = new_rom.get_character(unit_def.character_id)
            if unit_def.character_id in constants.characters.PLAYABLE_CHARACTERS:
                unit_def.class_id = new_character.default_class_id

            valid_replacements = [
                new_rom.get_item(id)
                for id in constants.items.WEAPON_RANDOMIZER_CANDIDATES
                if new_character.can_wield_weapon(new_rom.get_item(id))
            ]

            did_replacement = False
            for i in range(len(inv)):
                if inv[i] is None:
                    continue

                if (inv[i] in constants.items.WEAPON_RANDOMIZER_CANDIDATES) and (
                    len(valid_replacements) > 0
                ):
                    replacement = rng.choice(valid_replacements)
                    inv[i] = replacement.item_id
                elif inv[i] in constants.items.RANDOMIZABLE_CONSUMABLES:
                    if len(all_inv_consumables) > 0:
                        inv[i] = all_inv_consumables.pop().item_id
                elif inv[i] in constants.items.STAT_BOOSTERS:
                    if len(all_inv_stat_boosters) > 0:
                        inv[i] = all_inv_stat_boosters.pop().item_id

            unit_def.items = tuple(inv)
            unit_def.set_level(new_character.base_level)
            unit_def.save()
            unit_defs_modified += 1

        avg_enemy_level = 0
        if len(unit_def_levels) > 0:
            avg_enemy_level = sum(unit_def_levels) / len(unit_def_levels)

        print(
            f"{event_group.map_name} -- modified {unit_defs_modified} unit defs ({chapter_enemy_defs} enemies, {chapter_enemy_drops} item drops, avg level {avg_enemy_level:.1f}), {given_items_modified} given items, {chests_modified} chests, {shops_modified} shops"
        )

    for i in range(79):
        death_quote = CharacterDeathQuote.load(new_rom, 0x089ECD4C + (i * 0x0C))
        if death_quote.character.is_playable:
            death_quote.evolve(completion_event=0x65).save()

    # Modify two specific instructions in the main menu drawing code so that the New Game and Copy Data options don't appear when any save files are present.
    # Specifically, this modifies two comparisons within sub_80AB89C.
    new_rom.file.data[0x0AB8FC:0x0AB8FE] = b"\x00\x2d"
    new_rom.file.data[0x0AB8E8:0x0AB8EA] = b"\x00\x2d"
    new_rom.file.data[0x0AB8F8:0x0AB8FC] = b"\xe4\x46\xe4\x46"

    integration_data_path = Path(__file__).parent.parent.joinpath("integration")

    linker = Linker(new_rom)
    linker.load_external_data(integration_data_path.joinpath("fe8-symbols.json"))
    linker.load_elf(integration_data_path.joinpath("bin", "archipelago.o"))

    linker.duplicate_and_shim_thumb("sub_80A9250", "OnNewGameSave")
    linker.duplicate_and_shim_thumb("SaveGame", "OnGameSave")
    linker.duplicate_and_shim_thumb("LoadGame", "OnGameLoad")
    linker.duplicate_and_shim_thumb("CopyGameSave", "DisableSaveCopying")

    init_avail_state = bytearray(0x23)
    for char_data in patch_data.characters:
        if (
            char_data.precollected
            or char_data.send_item is None
            or char_data.send_item.player_id == patch_data.player_id
        ):
            init_avail_state[char_data.slot.id] = 1

    avail_state_section = linker.add_section(
        "avail_state",
        init_avail_state,
        None,
        section_type=SECTION_TYPE_ROM,
    )
    linker.add_symbol(
        "IsCharacterAvailable", 0, avail_state_section, SYM_TYPE_DATA, size=0x23
    )

    # This data really ought to be part of the Lua connector proper, but for now let's just stash it in the ROM.
    avail_data = b""
    avail_offsets = {}
    route_chapters = list(constants.characters.COMMON_CHAPTERS)
    if patch_data.eirika_route:
        route_chapters.extend(constants.characters.EIRIKA_CHAPTERS)
    else:
        route_chapters.extend(constants.characters.EPHRAIM_CHAPTERS)

    for chs in (
        constants.characters.COMMON_CHAPTERS,
        constants.characters.EIRIKA_CHAPTERS,
        constants.characters.EPHRAIM_CHAPTERS,
    ):
        for ch_id in chs:
            avail = constants.characters.AVAIL_MAP[ch_id]
            avail_offsets[f"BaseAvailabilityCh{ch_id}"] = len(avail_data)
            for char_id in range(0x23):
                avail_data += b"\x01" if char_id in avail else b"\x00"

    linker.add_section(
        "avail_map",
        bytearray(avail_data),
        avail_offsets,
        section_type=SECTION_TYPE_ROM,
    )

    # Create texts for 'character received' and 'item sent' messages.
    char_recv_text_ids = [0] * 0x23
    char_send_text_ids = [0] * 0x23
    for char_data in patch_data.characters:
        slot_id = char_data.slot.id
        char_recv_text_ids[slot_id] = len(new_rom.messages)

        msg_text = b"Received \x80\x21"
        msg_text += char_data.receive_item.item_name.encode("utf-8")
        if char_data.receive_item.player_id != patch_data.player_id:
            msg_text += b"\x80\x21 from \x80\x21"
            msg_text += char_data.receive_item.player_name.encode("utf-8")
        msg_text += b"\x80\x21.\x01\x03"
        new_rom.messages.append(Message(msg_text))

        if char_data.send_item is not None:
            char_send_text_ids[slot_id] = len(new_rom.messages)
            msg_text = b"Sent out \x80\x21"
            msg_text += char_data.send_item.player_name.encode("utf-8")
            msg_text += b"\x80\x21's \x80\x21"
            msg_text += char_data.send_item.item_name.encode("utf-8")
            msg_text += b"\x80\x21.\x01\x03"
            new_rom.messages.append(Message(msg_text))

    recv_table_data = b""
    send_table_data = b""
    for recv_id, send_id in zip(char_recv_text_ids, char_send_text_ids):
        recv_table_data += recv_id.to_bytes(2, "little", signed=False)
        send_table_data += send_id.to_bytes(2, "little", signed=False)

    ap_text_table_section = linker.add_section(
        "ap-text-ids", bytearray(recv_table_data + send_table_data)
    )
    linker.add_symbol(
        "UnitReceivedTextIds",
        0,
        ap_text_table_section,
        SYM_TYPE_DATA,
        size=len(recv_table_data),
    )
    linker.add_symbol(
        "UnitSentTextIds",
        len(recv_table_data),
        ap_text_table_section,
        SYM_TYPE_DATA,
        size=len(send_table_data),
    )

    inject_messages(linker, new_rom.messages)

    # Inject xorshift seed data
    linker.add_section(
        "xorshift-seed", bytearray(rng.randbytes(16)), {"Xorshift128_Init": 0}
    )
    linker.duplicate_and_shim_thumb("InitRN", "XorshiftInit")
    linker.duplicate_and_shim_thumb("NextRN", "XorshiftGenerate")
    linker.duplicate_and_shim_thumb("LoadRNState", "XorshiftLoad")
    linker.duplicate_and_shim_thumb("StoreRNState", "XorshiftStore")

    linker.duplicate_and_shim_thumb("sub_8085374", "OnGameOver")
    linker.duplicate_and_shim_thumb("TickActiveFactionTurn", "OnTickActiveFactionTurn")

    linker.add_section(
        "ap_data",
        bytearray(connector_port.to_bytes(2, "little", signed=False)),
        {"APConnectorPort": 0},
        section_type=SECTION_TYPE_ROM,
    )

    # Patch pointer to PlayerPhase_MainIdle:
    linker.add_rom_relocation(
        0x0059AB54, "PlayerPhase_MainIdleShim", relocation_types.OVERWRITE_32
    )

    linker.duplicate_and_shim_thumb("sub_80B93E0", "InterceptWMInputHandling")

    if patch_data.eirika_route:
        linker.add_rom_relocation(
            0x009F3664, "MenuAlwaysNotShown", relocation_types.OVERWRITE_32
        )
    else:
        linker.add_rom_relocation(
            0x009F3640, "MenuAlwaysNotShown", relocation_types.OVERWRITE_32
        )

    evt_patches = EventPatches(linker, new_rom)
    for ev_addr, chars in constants.characters.RECRUITMENT_EVENTS.items():
        s = ", ".join(f"{base_rom.get_character(c).name}" for c in chars)
        print(f"Processing event {ev_addr:08X} - {s}")
        patcher = evt_patches.get_patcher(ev_addr)

        for i, char_id in enumerate(chars):
            patcher.set_val(i + 1, char_id)

        for i in range(len(chars), 4):
            patcher.set_val(i + 1, 0)

        # evbit_modify here so that players don't skip the effects
        patcher.evbit_modify(3).asmc("ASMCOnUnitRecruited")

        # Skip warp effects if this is a chapter end event
        for char_id in chars:
            patcher.set_val(1, char_id).asmc("ASMCPrepareUnitDisappearEffect")
            if ev_addr not in constants.characters.SKIP_WARP_EVENTS:
                skip_label = patcher.alloc_label()
                patcher.beq(1, 0, skip_label).warp_out(None).warp_end().label(
                    skip_label
                )
        patcher.set_evbit(7, True)

    # Patch certain chapter end events to ensure that missed recruits are added to the party:
    for ev_addr, chars in constants.characters.MISSABLE_RECRUIT_CATCHUPS.items():
        patcher = evt_patches.get_patcher(ev_addr)
        catchup_event = evt_patches.new_patcher().evbit_modify(3)

        for i, char_id in enumerate(chars):
            catchup_event.set_val(i + 1, char_id)

        for i in range(len(chars), 4):
            catchup_event.set_val(i + 1, 0)

        catchup_event.asmc("ASMCOnUnitRecruited")
        for char_id in chars:
            # The event called here handily ensures a unit is added to the party by
            # loading them and changing their allegiance as necessary.
            catchup_event.set_val(2, char_id).call(0x089EE5BC)

        catchup_event.evbit_modify(0)
        patcher.call(catchup_event, position=0)

    for village_cond in constants.characters.REQUIRED_VILLAGE_DESTROYED_EVENTS:
        cond = evt_patches.get_event_condition(village_cond)
        cond.evolve(complete_flag=0x65).save()

    for ev_addr in constants.characters.FINAL_BOSS_DEFEAT_EVENTS:
        patcher = evt_patches.get_patcher(ev_addr)
        patcher.asmc("ASMCSendVictoryEvent", position=0)

    evt_patches.finalize()

    return linker.link()
