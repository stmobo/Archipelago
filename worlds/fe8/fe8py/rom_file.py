from __future__ import annotations

from typing import BinaryIO, Union

ROM_BASE_ADDRESS = 0x0800_0000
ROM_MAX_SIZE = 0x200_0000
ROM_MAX_ADDRESS = ROM_BASE_ADDRESS + ROM_MAX_SIZE


class ReadOnlyError(Exception):
    def __str__(self) -> str:
        return "Attempted to modify immutable ROM data"


def is_valid_rom_address(addr: int) -> bool:
    return addr >= ROM_BASE_ADDRESS and addr < (ROM_BASE_ADDRESS + ROM_MAX_SIZE)


def ensure_file_offset(addr: int) -> int:
    if addr < ROM_MAX_SIZE:
        return addr
    elif addr >= ROM_MAX_SIZE and addr < ROM_BASE_ADDRESS:
        raise ValueError("{:08x} is not a valid file offset".format(addr))
    elif addr >= ROM_BASE_ADDRESS and addr < (ROM_BASE_ADDRESS + ROM_MAX_SIZE):
        return addr - ROM_BASE_ADDRESS
    else:
        raise ValueError("{:08x} is not a valid ROM memory address".format(addr))


def ensure_rom_address(addr: int) -> int:
    if addr < ROM_MAX_SIZE:
        return addr + ROM_BASE_ADDRESS
    elif addr >= ROM_MAX_SIZE and addr < ROM_BASE_ADDRESS:
        raise ValueError("{:08x} is not a valid file offset".format(addr))
    elif addr >= ROM_BASE_ADDRESS and addr < (ROM_BASE_ADDRESS + ROM_MAX_SIZE):
        return addr
    else:
        raise ValueError("{:08x} is not a valid ROM memory address".format(addr))


class ROMFile:
    data: bytearray
    _immutable: bool

    def __init__(
        self,
        source: Union[bytes, bytearray, BinaryIO, ROMFile],
        immutable: bool = False,
    ):
        self._immutable = immutable

        try:
            self.data = source.data
        except AttributeError:
            try:
                self.data = source.read()
            except AttributeError:
                self.data = bytearray(source)

    @property
    def immutable(self) -> bool:
        return self._immutable

    def make_immutable(self):
        self._immutable = True

    def expand(self, new_sz: int):
        if self.immutable:
            raise ReadOnlyError()
        new_sz = max(len(self.data), new_sz)
        new_data = bytearray(new_sz)
        new_data[: len(self.data)] = self.data
        self.data = new_data

    def read_int(self, where: int, sz: int, *, signed=False) -> int:
        addr = ensure_file_offset(where)
        return int.from_bytes(self.data[addr : addr + sz], "little", signed=signed)

    def write_int(self, value: int, where: int, sz: int, *, signed=False):
        if self.immutable:
            raise ReadOnlyError()
        addr = ensure_file_offset(where)
        self.data[addr : addr + sz] = value.to_bytes(sz, "little", signed=signed)

    def read_bytes(self, where: int, sz: int) -> bytes:
        addr = ensure_file_offset(where)
        return self.data[addr : addr + sz]

    def read_byte_range(self, start: int, end: int) -> bytes:
        start = ensure_file_offset(start)
        end = ensure_file_offset(end)
        return self.data[start:end]

    def write_bytes(self, value: bytes, where: int):
        if self.immutable:
            raise ReadOnlyError()
        addr = ensure_file_offset(where)
        self.data[addr : addr + len(value)] = value

    def read_addr(self, where: int) -> int:
        return ensure_rom_address(self.read_int(where, 4, signed=False))

    def write_addr(self, value: int, where: int):
        if self.immutable:
            raise ReadOnlyError()
        self.write_int(ensure_rom_address(value), where, 4, signed=False)
