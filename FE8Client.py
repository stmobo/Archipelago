from __future__ import annotations

import asyncio
import json
import os.path as osp
import random
import subprocess as sp
from pathlib import Path
from typing import Dict, Optional, Set

import Utils
from CommonClient import (
    ClientStatus,
    CommonContext,
    get_base_parser,
    gui_enabled,
    logger,
    server_loop,
)
from Utils import async_start
from worlds.fe8.fe8py.connector import (
    CharacterRecruitEvent,
    ConnectionClosedError,
    ConnectionTimeoutError,
    FE8Connection,
    GameOverEvent,
    KeepaliveEvent,
    VictoryEvent,
)
from worlds.fe8.fe8py.constants.characters import CharacterFill, CharacterSlot
from worlds.fe8.fe8py.local_patcher import PatcherData, patch_rom
from worlds.fe8.fe8py.rom import ROM


class FE8Context(CommonContext):
    game = "Fire Emblem The Sacred Stones"
    seen_locations: Set[int]
    patch_data: PatcherData
    awaiting_deathlink: asyncio.Event

    def __init__(self, patch_data: PatcherData, server_address, password):
        super().__init__(server_address, password)
        self.patch_data = patch_data
        self.auth = patch_data.player_name
        self.items_handling = 0b111
        self.seen_locations = set()
        self.awaiting_deathlink = asyncio.Event()

    async def server_auth(self, password_requested: bool = False):
        if password_requested and not self.password:
            await super(FE8Context, self).server_auth(password_requested)
        await self.send_connect()

    def on_deathlink(self, data: dict):
        if self.patch_data.death_link:
            self.awaiting_deathlink.set()
        super().on_deathlink(data)


async def run_game(romfile):
    # TODO: don't hardcode this lmao
    sp.Popen(
        [
            Path.home().joinpath("Downloads", "BizHawk-2.8-win-x64", "EmuHawk.exe"),
            "--lua="
            + Path.cwd().joinpath("data", "lua", "FE8", "fe8_connector.lua").as_posix(),
            romfile,
        ],
        stdin=sp.DEVNULL,
        stdout=sp.DEVNULL,
        stderr=sp.DEVNULL,
    )
    # auto_start = Utils.get_options()["fe8_options"].get("rom_start", True)
    # if auto_start is True:
    #     import webbrowser

    #     webbrowser.open(romfile)
    # elif osp.isfile(auto_start):
    #     sp.Popen(
    #         [auto_start, romfile],
    #         stdin=sp.DEVNULL,
    #         stdout=sp.DEVNULL,
    #         stderr=sp.DEVNULL,
    #     )


async def deathlink_handler(ctx: FE8Context, connection: FE8Connection):
    while True:
        await ctx.awaiting_deathlink.wait()
        await connection.trigger_game_over()
        ctx.awaiting_deathlink.clear()


async def handle_connector_events(
    ctx: FE8Context, patch_data: PatcherData, connection: FE8Connection
):
    item_id_to_slot: Dict[int, CharacterSlot] = {}
    slot_id_to_location_id: Dict[int, Optional[int]] = {}
    slot_id_to_fill: Dict[int, CharacterFill] = {}

    for character in patch_data.characters:
        item_id_to_slot[character.receive_item.item_id] = character.slot
        slot_id_to_location_id[character.slot.id] = character.location_id
        slot_id_to_fill[character.slot.id] = character.fill

    while True:
        event = await connection.get_event()
        if isinstance(event, KeepaliveEvent):
            unlocked_chars = set()
            for character in patch_data.characters:
                if character.precollected:
                    unlocked_chars.add(character.slot.id)
            for item in ctx.items_received:
                unlocked_chars.add(item_id_to_slot[item.item].id)
            await connection.sync_unlocked_units(sorted(unlocked_chars))
        elif isinstance(event, CharacterRecruitEvent):
            new_chars = [
                char_id
                for char_id in event.characters
                if char_id not in ctx.seen_locations
            ]

            location_ids = [
                slot_id_to_location_id[char_id] for char_id in event.characters
            ]

            await asyncio.gather(
                ctx.send_msgs([{"cmd": "LocationChecks", "locations": location_ids}]),
                connection.enqueue_active_event_response(*new_chars),
            )
            ctx.seen_locations.update(event.characters)
        elif isinstance(event, VictoryEvent):
            ctx.finished_game = True
            ctx.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])
        elif isinstance(event, GameOverEvent) and "DeathLink" in ctx.tags:
            dead_chars = [slot_id_to_fill[char_id] for char_id in event.characters]
            # We should only ever get one dead character at a time, but handling multiple simultaneous deaths isn't that hard.
            if len(dead_chars) == 0:
                msg = ""
            elif len(dead_chars) == 1:
                msg = f"{dead_chars[0].name} has been defeated in {ctx.auth}'s world!"
            elif len(dead_chars) == 2:
                msg = f"{dead_chars[0].name} and {dead_chars[1].name} have been defeated in {ctx.auth}'s world!"
            elif len(dead_chars) > 2:
                names_first = ", ".join(c.name for c in dead_chars[:-1])
                msg = f"{names_first}, and {dead_chars[-1].name} have been defeated in {ctx.auth}'s world!"
            await ctx.send_death(msg)


async def connect_to_fe8(ctx: FE8Context, patch_data: PatcherData, connector_port: int):
    while not ctx.exit_event.is_set():
        try:
            connection = await asyncio.wait_for(
                FE8Connection.connect("localhost", connector_port), 5
            )
        except OSError as e:
            logger.error(f"Could not connect to FE8: {e}. Retrying...")
            continue
        except asyncio.TimeoutError:
            logger.error(f"Connection to FE8 timed out, retrying...")
            continue

        logger.info("Connected to FE8.")
        await ctx.update_death_link(patch_data.death_link)
        if patch_data.death_link:
            logger.info("DeathLink enabled.")

        exit_task = asyncio.create_task(ctx.exit_event.wait(), name="Exit Event Task")
        packet_task = asyncio.create_task(connection.run(), name="Connector Read Task")
        deathlink_task = asyncio.create_task(
            deathlink_handler(ctx, connection), name="DeathLink Handler Task"
        )
        event_task = asyncio.create_task(
            handle_connector_events(ctx, patch_data, connection),
            name="Sync Event Handler",
        )

        try:
            # Wait for either the packet reader or event handler tasks to raise an exception,
            # or for the exit event to be set.
            done, pending = await asyncio.wait(
                (packet_task, event_task, exit_task, deathlink_task),
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Cancel pending tasks.
            for task in pending:
                task.cancel()

            # Wait for them to die.
            for task in pending:
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            # Get results/exceptions from whatever task completed.
            for task in done:
                await task
        except OSError as e:
            logger.error(f"Connection to FE8 failed: {e}, attempting to reconnect...")
        except ConnectionTimeoutError:
            logger.error(f"Connection to FE8 timed out, attempting to reconnect...")
        except ConnectionClosedError:
            # TODO: reconnect when not debugging
            logger.error("FE8 connector server shut down, exiting.")
            ctx.exit_event.set()
        finally:
            await connection.close()
    logger.info("Client exiting.")


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

        ctx = FE8Context(patch_data, args.connect, args.password)
        ctx.server_task = asyncio.create_task(server_loop(ctx), name="ServerLoop")
        connector_task = asyncio.create_task(
            connect_to_fe8(ctx, patch_data, connector_port), name="GBA Sync"
        )

        # if gui_enabled:
        #     ctx.run_gui()
        async_start(run_game(out_path))
        ctx.run_cli()

        await ctx.exit_event.wait()
        ctx.server_address = None

        await ctx.shutdown()
        await connector_task

    import colorama

    colorama.init()

    asyncio.run(main())
    colorama.deinit()
