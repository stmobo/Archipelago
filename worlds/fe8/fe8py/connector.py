from __future__ import annotations

import asyncio
import struct
from typing import Dict, List, Optional, Tuple, Union

HEADER_FMT = ">II"
KEEPALIVE_TIMEOUT = 15


class CommandError(Exception):
    def __init__(self, msg: str, *args: object) -> None:
        self.msg = msg
        super().__init__(*args)

    def __str__(self) -> str:
        return f"Emulator connector returned error: {self.msg}"


class ConnectionClosedError(Exception):
    def __str__(self) -> str:
        return f"Server connection closed unexpectedly"


class ConnectionTimeoutError(Exception):
    def __str__(self) -> str:
        return f"Server connection timed out"


class KeepaliveEvent:
    pass


class VictoryEvent:
    pass


class GameOverEvent:
    characters: Tuple[int, ...]  # list of characters that are dead

    def __init__(self, characters: Tuple[int, ...]) -> None:
        self.characters = characters


class CharacterRecruitEvent:
    characters: Tuple[int, ...]

    def __init__(self, characters: Tuple[int, ...]) -> None:
        self.characters = characters


class FE8Connection:
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    cur_req_id: int
    request_futures: Dict[int, asyncio.Future]
    events: asyncio.Queue

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self.cur_req_id = 0
        self.request_futures = {}
        self.events = asyncio.Queue()

    @classmethod
    async def connect(cls, host: str, port: int) -> FE8Connection:
        reader, writer = await asyncio.open_connection(host, port)
        ret = cls(reader, writer)
        return ret

    def _init_request(self) -> Tuple[int, asyncio.Future]:
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        req_id = self.cur_req_id
        self.request_futures[req_id] = fut
        self.cur_req_id += 1
        return req_id, fut

    async def _read_packet(self) -> Tuple[int, bytes]:
        try:
            header = await self.reader.readexactly(8)
            payload_len, packet_type = struct.unpack(HEADER_FMT, header)
            payload = await self.reader.readexactly(payload_len)
            return packet_type, payload
        except asyncio.IncompleteReadError:
            raise ConnectionClosedError() from None

    async def _write_packet(self, packet_type: int, data: bytes):
        header = struct.pack(HEADER_FMT, len(data), packet_type)
        self.writer.write(header + data)
        await self.writer.drain()

    async def close(self):
        self.writer.close()
        await self.writer.wait_closed()

    async def run(self):
        while True:
            try:
                packet_type, payload = await asyncio.wait_for(
                    self._read_packet(), KEEPALIVE_TIMEOUT
                )
            except asyncio.TimeoutError:
                raise ConnectionTimeoutError() from None

            if packet_type == 0:  # Keepalive
                self.events.put_nowait(KeepaliveEvent())
            elif packet_type == 1:  # Request response
                req_id = struct.unpack(">I", payload[:4])[0]
                try:
                    future = self.request_futures[req_id]
                    future.set_result(payload[4:])
                    del self.request_futures[req_id]
                except KeyError:
                    pass
            elif packet_type == 2:  # Character recruitment event
                unlocked: Tuple[int, int, int, int] = struct.unpack(
                    ">BBBB", payload[:4]
                )

                unlocked = tuple(char_id for char_id in unlocked if char_id != 0)
                self.events.put_nowait(CharacterRecruitEvent(unlocked))
            elif packet_type == 3:  # Victory event
                self.events.put_nowait(VictoryEvent())
            elif packet_type == 4:  # Game over event
                _, n_dead = struct.unpack(">IH", payload[:6])
                characters = tuple(payload[6 : 6 + n_dead])
                self.events.put_nowait(GameOverEvent(characters))

    async def sync_unlocked_units(
        self, unlocked_chars: List[int], *, queue_events: bool = True
    ):
        statuses = [0] * 0x22
        for char_id in unlocked_chars:
            statuses[char_id - 1] = 1

        req_id, fut = self._init_request()
        req_payload = struct.pack(">I34B", req_id, *statuses)

        if queue_events:
            await self._write_packet(1, req_payload)
        else:
            await self._write_packet(4, req_payload)

        payload: bytes = await fut
        if payload[0] == 1:
            return payload[1:]
        else:
            raise CommandError(payload[1:].decode("utf-8"))

    async def enqueue_active_event_response(self, *textIds: int):
        req_id, fut = self._init_request()
        req_data = struct.pack(">IB", req_id, len(textIds))
        for id in textIds:
            req_data = req_data + id.to_bytes(2, "big", signed=False)
        await self._write_packet(2, req_data)

        payload: bytes = await fut
        if payload[0] == 1:
            return payload[1:]
        else:
            raise CommandError(payload[1:].decode("utf-8"))

    async def trigger_game_over(self):
        req_id, fut = self._init_request()
        await self._write_packet(3, struct.pack(">I", req_id))

        payload: bytes = await fut
        if payload[0] == 1:
            return payload[1:]
        else:
            raise CommandError(payload[1:].decode("utf-8"))

    async def get_event(
        self,
    ) -> Union[KeepaliveEvent, CharacterRecruitEvent, GameOverEvent, VictoryEvent]:
        if self.writer.is_closing():
            raise ConnectionClosedError()
        return await self.events.get()
