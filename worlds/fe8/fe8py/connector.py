from __future__ import annotations

import asyncio
import struct
from typing import Dict, List, Tuple, Union

HEADER_FMT = ">II"


class CommandError(Exception):
    def __init__(self, msg: str, *args: object) -> None:
        self.msg = msg
        super().__init__(*args)

    def __str__(self) -> str:
        return f"Emulator connector returned error: {self.msg}"


class KeepaliveEvent:
    pass


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
    process_task: asyncio.Task

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self.cur_req_id = 0
        self.request_futures = {}
        self.events = asyncio.Queue()
        self.process_task = None

    @classmethod
    async def connect(cls, host: str, port: int) -> FE8Connection:
        reader, writer = await asyncio.open_connection(host, port)
        ret = cls(reader, writer)
        ret.process_task = asyncio.create_task(ret.process_incoming_packets())
        return ret

    def _init_request(self) -> Tuple[int, asyncio.Future]:
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        req_id = self.cur_req_id
        self.request_futures[req_id] = fut
        self.cur_req_id += 1
        return req_id, fut

    async def write_packet(self, packet_type: int, data: bytes):
        header = struct.pack(HEADER_FMT, len(data), packet_type)
        self.writer.write(header + data)
        await self.writer.drain()

    async def process_incoming_packets(self):
        while True:
            header = await self.reader.readexactly(8)
            payload_len, packet_type = struct.unpack(HEADER_FMT, header)
            payload = await self.reader.readexactly(payload_len)

            if packet_type == 0:
                self.events.put_nowait(KeepaliveEvent())
            elif packet_type == 1:
                req_id = struct.unpack(">I", payload[:4])[0]
                try:
                    future = self.request_futures[req_id]
                    future.set_result(payload[4:])
                    del self.request_futures[req_id]
                except KeyError:
                    pass
            elif packet_type == 2:
                unlocked: Tuple[int, int, int, int] = struct.unpack(
                    ">BBBB", payload[:4]
                )

                unlocked = tuple(char_id for char_id in unlocked if char_id != 0)
                self.events.put_nowait(CharacterRecruitEvent(unlocked))

    async def sync_unlocked_units(self, unlocked_chars: List[int]):
        statuses = [0] * 0x22
        for char_id in unlocked_chars:
            statuses[char_id - 1] = 1

        req_id, fut = self._init_request()
        await self.write_packet(1, struct.pack(">I34B", req_id, *statuses))

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
        await self.write_packet(2, req_data)

        payload: bytes = await fut
        if payload[0] == 1:
            return payload[1:]
        else:
            raise CommandError(payload[1:].decode("utf-8"))

    async def get_event(self) -> Union[KeepaliveEvent, CharacterRecruitEvent]:
        return await self.events.get()
