from __future__ import annotations

import asyncio
import json
import os.path as osp
import random
import subprocess as sp
from pathlib import Path
from typing import Optional, Set

import Utils
from CommonClient import (
    ClientCommandProcessor,
    CommonContext,
    get_base_parser,
    gui_enabled,
    logger,
    server_loop,
)
from Utils import async_start
from worlds.fe8 import fe8py
from worlds.fe8.fe8py.connector import (
    CharacterRecruitEvent,
    ConnectionClosedError,
    ConnectionTimeoutError,
    FE8Connection,
    KeepaliveEvent,
)
from worlds.fe8.fe8py.constants.characters import CharacterSlot
from worlds.fe8.fe8py.local_patcher import PatcherData, patch_rom
from worlds.fe8.fe8py.rom import ROM


class FE8Context(CommonContext):
    game = "Fire Emblem The Sacred Stones"
    seen_locations: Set[int]
    patch_data: PatcherData

    def __init__(self, patch_data: PatcherData, server_address, password):
        super().__init__(server_address, password)
        self.patch_data = patch_data
        self.auth = patch_data.player_name
        self.items_handling = 0b111
        self.seen_locations = set()

    async def server_auth(self, password_requested: bool = False):
        if password_requested and not self.password:
            await super(FE8Context, self).server_auth(password_requested)
        await self.send_connect()


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


async def handle_connector_events(
    ctx: FE8Context, patch_data: PatcherData, connection: FE8Connection
):
    while True:
        event = await connection.get_event()
        if isinstance(event, KeepaliveEvent):
            unlocked_chars = set()
            for character in patch_data.characters:
                if character.precollected:
                    # logger.info(
                    #     f"Have character {character.slot.id:02X} ({character.slot.name})"
                    # )
                    unlocked_chars.add(character.slot.id)
            for item in ctx.items_received:
                slot = CharacterSlot.from_ap_id(item.item)
                # logger.info(f"Have character {slot.id:02X} ({slot.name})")
                unlocked_chars.add(slot.id)
            await connection.sync_unlocked_units(sorted(unlocked_chars))
        elif isinstance(event, CharacterRecruitEvent):
            new_chars = [
                char_id
                for char_id in event.characters
                if char_id not in ctx.seen_locations
            ]

            location_ids = [
                CharacterSlot.from_id(char_id).ap_id for char_id in event.characters
            ]

            await asyncio.gather(
                ctx.send_msgs([{"cmd": "LocationChecks", "locations": location_ids}]),
                connection.enqueue_active_event_response(*new_chars),
            )
            ctx.seen_locations.update(event.characters)


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
        exit_task = asyncio.create_task(ctx.exit_event.wait(), name="Exit Event Task")
        packet_task = asyncio.create_task(connection.run(), name="Connector Read Task")
        event_task = asyncio.create_task(
            handle_connector_events(ctx, patch_data, connection),
            name="Sync Event Handler",
        )

        try:
            # Wait for either the packet reader or event handler tasks to raise an exception,
            # or for the exit event to be set.
            done, pending = await asyncio.wait(
                (packet_task, event_task, exit_task),
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
