from __future__ import annotations

import asyncio
import json
import os.path as osp
import random
import subprocess as sp
from typing import Optional, Set

import Utils
from CommonClient import (ClientCommandProcessor, CommonContext,
                          get_base_parser, gui_enabled, logger, server_loop)
from Utils import async_start
from worlds.fe8 import fe8py
from worlds.fe8.fe8py.connector import (CharacterRecruitEvent, FE8Connection,
                                        KeepaliveEvent)
from worlds.fe8.fe8py.constants.characters import CharacterSlot
from worlds.fe8.fe8py.local_patcher import PatcherData, patch_rom
from worlds.fe8.fe8py.rom import ROM


class FE8Context(CommonContext):
    game = "Fire Emblem: The Sacred Stones"
    seen_locations: Set[int]
    sync_task: Optional[asyncio.Task]

    def __init__(self, server_address, password):
        super().__init__(server_address, password)
        self.seen_locations = set()
        self.sync_task = None


async def run_game(romfile):
    auto_start = Utils.get_options()["fe8_options"].get("rom_start", True)
    if auto_start is True:
        import webbrowser

        webbrowser.open(romfile)
    elif osp.isfile(auto_start):
        sp.Popen(
            [auto_start, romfile],
            stdin=sp.DEVNULL,
            stdout=sp.DEVNULL,
            stderr=sp.DEVNULL,
        )


async def sync_task(ctx: FE8Context, connector_port: int):
    connection = await FE8Connection.connect("localhost", connector_port)
    while not ctx.exit_event.is_set():
        try:
            event = await asyncio.wait_for(connection.get_event(), 10)
        except asyncio.TimeoutError:
            logger.error("FE8 connection timed out?")
            continue

        if isinstance(event, KeepaliveEvent):
            unlocked_chars = []
            for item in ctx.items_received:
                slot = CharacterSlot.from_ap_id(item.item)
                unlocked_chars.append(slot.id)
            await connection.sync_unlocked_units(unlocked_chars)
        elif isinstance(event, CharacterRecruitEvent):
            new_chars = [
                char_id
                for char_id in event.characters
                if char_id not in ctx.seen_locations
            ]

            location_ids = [
                CharacterSlot.from_id(char_id).ap_id for char_id in event.characters
            ]

            await ctx.send_msgs([{"cmd": "LocationChecks", "locations": location_ids}])

            await connection.enqueue_active_event_response(*new_chars)
            ctx.seen_locations.update(event.characters)


if __name__ == "__main__":
    Utils.init_logging("FE8Client")

    options = Utils.get_options()

    async def main():
        parser = get_base_parser()
        parser.add_argument("base_rom", type=str, help="Path to a base rom to patch")
        parser.add_argument(
            "patch_data", type=str, help="Path to an APFE8 patch data file"
        )
        args = parser.parse_args()

        with open(args.patch_data, "r", encoding="utf-8") as f:
            patch_data = PatcherData.from_dict(json.load(f))

        with open(args.base_rom, "rb") as f:
            base_rom = ROM.load(f.read(), True)

        connector_port = random.randint(9000, 50000)
        out_path = osp.splitext(args.patch_data)[0] + ".gba"
        logger.info(
            f"Beginning patching process with connector port: {connector_port}."
        )
        patched = patch_rom(base_rom, patch_data, connector_port)
        with open(out_path, "wb") as f:
            f.write(patched)

        ctx = FE8Context(args.connect, args.password)
        ctx.server_task = asyncio.create_task(server_loop(ctx), name="ServerLoop")
        if gui_enabled:
            ctx.run_gui()
        ctx.run_cli()
        ctx.sync_task = asyncio.create_task(
            sync_task(ctx, connector_port), name="GBA Sync"
        )

        async_start(run_game(out_path))

        await ctx.exit_event.wait()
        ctx.server_address = None

        await ctx.shutdown()

        if ctx.sync_task:
            await ctx.sync_task

    import colorama

    colorama.init()

    asyncio.run(main())
    colorama.deinit()
