from __future__ import annotations

import heapq
import re
import sys
from collections import deque
from functools import total_ordering
from typing import (TYPE_CHECKING, Deque, Dict, Iterable, Iterator, List,
                    Optional, Set, Tuple, Union)

from .linker import relocation_types
from .rom_file import ROMFile, ensure_file_offset

if TYPE_CHECKING:
    from .linker import Linker, relocation_types

MESSAGE_SPECIAL_CHARS = {
    b"\x93": "“",
    b"\x94": "”",
    b"\xE9": "é",
}


@total_ordering
class HuffmanTree:
    left: Optional[HuffmanTree] = None
    right: Optional[HuffmanTree] = None
    data: Optional[bytes] = None
    freq: Optional[int] = None

    def __init__(self, left, right, data=None, freq=None):
        self.left = left
        self.right = right
        self.data = data
        self.freq = freq

    @property
    def is_leaf(self) -> bool:
        return (self.left is None) or (self.right is None)

    @property
    def is_terminal(self) -> bool:
        return self.is_leaf and (self.data is None)

    @classmethod
    def from_bytes(cls, data: bytes, index: Optional[int] = None) -> HuffmanTree:
        if index is not None:
            base_offset = index * 4
            node_bytes = data[base_offset : base_offset + 4]
        else:
            node_bytes = data[-4:]

        right = int.from_bytes(node_bytes[2:4], "little", signed=False)
        if right & 0x8000 == 0:  # internal node
            left_idx = int.from_bytes(node_bytes[:2], "little", signed=False)
            return cls(
                HuffmanTree.from_bytes(data, left_idx),
                HuffmanTree.from_bytes(data, right),
            )
        elif node_bytes[0] == 0 and node_bytes[1] == 0:  # terminal symbol
            return cls(None, None, data=None)
        elif node_bytes[1] != 0:  # two-byte symbol
            return cls(None, None, data=node_bytes[:2])
        else:  # one-byte symbol
            return cls(None, None, data=node_bytes[:1])

    @classmethod
    def load_from_rom(cls, rom: ROMFile) -> HuffmanTree:
        start_addr = rom.read_addr(0x6E0)
        end_addr = rom.read_addr(rom.read_addr(0x6DC))
        return HuffmanTree.from_bytes(rom.read_byte_range(start_addr, end_addr + 4))

    @classmethod
    def build(cls, messages: Iterable[bytes], *, force_total: bool = False) -> HuffmanTree:
        freq_table: Dict[bytes, int] = {}

        if force_total:
            for i in range(256):
                freq_table[bytes((i,))] = 0
                for j in range(256):
                    freq_table[bytes((i, j))] = 0

        for msg in messages:
            for i in range(0, len(msg), 2):
                symbol = msg[i : i + 2]
                freq_table[symbol] = freq_table.get(symbol, 0) + 1
            freq_table[None] = freq_table.get(b"", 0) + 1  # terminal symbol

        # min-heap by frequency (least common symbols first)
        queue: List[HuffmanTree] = [
            HuffmanTree(None, None, data=symbol, freq=freq)
            for (symbol, freq) in freq_table.items()
        ]

        heapq.heapify(queue)
        while len(queue) > 1:
            # take the two nodes with the least frequency in the queue,
            # and create a new internal node with them as children
            left = heapq.heappop(queue)
            right = heapq.heappop(queue)
            heapq.heappush(
                queue, HuffmanTree(left, right, data=None, freq=left.freq + right.freq)
            )

        # the last remaining node is the root
        return queue.pop()

    def to_bytes(self, start_index: int = 0) -> bytes:
        if self.is_terminal:
            return b"\x00\x00\x00\x80"
        elif self.is_leaf:
            if len(self.data) == 1:
                return self.data + b"\x00\x00\x80"
            else:
                return self.data + b"\x00\x80"
        else:
            ret = self.left.to_bytes(start_index)
            left_index = start_index + ((len(ret) // 4) - 1)
            ret += self.right.to_bytes(left_index + 1)
            right_index = start_index + ((len(ret) // 4) - 1)
            return (
                ret
                + left_index.to_bytes(2, "little", signed=False)
                + right_index.to_bytes(2, "little", signed=False)
            )

    def write_to_rom(self, rom: ROMFile, start_addr: int) -> int:
        node_data = self.to_bytes()
        rom.write_bytes(node_data, start_addr)
        rom.write_addr(start_addr, 0x6E0)
        rom.write_addr(start_addr + len(node_data) - 4, rom.read_addr(0x6DC))
        return len(node_data)

    def decode(self, data: bytes, start_offset: int) -> bytes:
        cur_offset: int = start_offset
        cur_byte: int = data[start_offset]
        cur_bit: int = 0
        cur_node: HuffmanTree = self
        ret = b""

        while True:
            next_bit = (cur_byte & 1) != 0
            cur_byte >>= 1
            cur_bit += 1
            if cur_bit == 8:
                cur_offset += 1
                cur_byte = data[cur_offset]
                cur_bit = 0

            if next_bit:
                cur_node = cur_node.right
            else:
                cur_node = cur_node.left

            if cur_node.is_terminal:
                return ret
            elif cur_node.is_leaf:
                ret += cur_node.data
                cur_node = self
            # else return to start of loop

    def get_encoder(self) -> HuffmanEncoder:
        return HuffmanEncoder(self._iter_symbols())

    def _iter_symbols(
        self, cur_bits: int = 0, cur_len: int = 0
    ) -> Iterator[Tuple[Optional[bytes], Tuple[int, int]]]:
        if self.is_leaf:
            yield (self.data, (cur_bits, cur_len))
        else:
            yield from self.left._iter_symbols(cur_bits, cur_len + 1)
            yield from self.right._iter_symbols(cur_bits | (1 << cur_len), cur_len + 1)

    def __eq__(self, other: HuffmanTree):
        if isinstance(other, HuffmanTree):
            return self.freq == other.freq
        else:
            return NotImplemented

    def __lt__(self, other: HuffmanTree):
        if isinstance(other, HuffmanTree):
            return self.freq < other.freq
        else:
            return NotImplemented


class HuffmanEncoder:
    symbols: Dict[Optional[bytes], Tuple[int, int]]

    def __init__(self, symbols):
        self.symbols = dict(symbols)

    def encode(self, data: bytes) -> bytes:
        # map symbols in data (+ terminal symbol) to bit encodings
        encoded_symbols: List[Tuple[int, int]] = [
            self.symbols[data[i : i + 2]] for i in range(0, len(data), 2)
        ]
        encoded_symbols.append(self.symbols[None])

        ret = b""
        cur_bit_idx = 0
        cur_bits = 0
        for bits, sym_len in encoded_symbols:
            cur_bits |= bits << cur_bit_idx
            cur_bit_idx += sym_len

            while cur_bit_idx >= 8:
                ret += (cur_bits & 0xFF).to_bytes(1, "little", signed=False)
                cur_bit_idx -= 8
                cur_bits >>= 8
            cur_bits &= 0xFF  # mask out sign extension

        # add remaining bits (if any) to result
        if cur_bit_idx > 0:
            ret += cur_bits.to_bytes(1, "little", signed=False)
        return ret


class Message:
    parts: List[Union[str, bytes]]

    def __init__(self, source: Union[Message, bytes]) -> None:
        try:
            self.parts = list(source.parts)
        except AttributeError:
            self.parts = []
            part: bytes
            for i, part in enumerate(
                re.split(rb"(\x80.|\x10.|[^\x20-\x7e\x93\x94\xe9])", source)
            ):
                if i % 2 == 0:
                    for byte, repl in MESSAGE_SPECIAL_CHARS.items():
                        part = part.replace(byte, repl.encode("utf-8"))
                    if len(part) > 0:
                        self.parts.append(part.decode("utf-8"))
                else:
                    self.parts.append(part)

    def iter_text(self) -> Iterator[str]:
        return filter(lambda p: isinstance(p, str), self.parts)

    def to_bytes(self) -> bytes:
        ret = b""
        for part in self.parts:
            if isinstance(part, str):
                part = part.encode("utf-8")
                for byte, repl in MESSAGE_SPECIAL_CHARS.items():
                    part = part.replace(repl.encode("utf-8"), byte)
            ret += part
        return ret

    def __str__(self) -> str:
        return " ".join(self.iter_text()).strip()


def replace_names(
    messages: Iterable[Message],
    replacements: Dict[str, str],
    portrait_replacements: Dict[int, int],
):
    portrait_pattern = rb"\x10(.)"
    pattern = (
        r"(?<!\w)((?:[A-Z]-)*)(" + "|".join(map(re.escape, replacements.keys())) + ")"
    )

    def _replace_match(match: re.Match) -> str:
        nonlocal replacements
        ret = replacements[match.group(2)]
        if match.group(1) is not None and len(match.group(1)) > 0:
            # fixup stuttering
            n = len(match.group(1)) // 2
            ret = ((ret[0] + "-") * n) + ret
        return ret

    def _replace_portrait_match(match: re.Match) -> bytes:
        nonlocal portrait_replacements
        try:
            return b"\x10" + portrait_replacements[match[1][0]].to_bytes(1, "little")
        except KeyError:
            return match[0]

    for i, message in enumerate(messages):
        for j, part in enumerate(message.parts):
            if isinstance(part, str):
                message.parts[j] = re.sub(pattern, _replace_match, part)
            else:
                message.parts[j] = re.sub(
                    portrait_pattern, _replace_portrait_match, part
                )

        print(
            "Processed character replacements in {:4d}/{} messages...".format(
                i, len(messages)
            ),
            end="\r",
            file=sys.stderr,
        )
    print(
        "Processed character replacements in {}/{} messages".format(
            len(messages), len(messages)
        ),
        file=sys.stderr,
    )


def load_messages(rom: ROMFile) -> List[Message]:
    huff_tree = HuffmanTree.load_from_rom(rom)
    table_addr = rom.read_addr(0xA2A0)
    messages = []
    for i in range(0x0D4B):
        text_addr = rom.read_addr(table_addr + (i * 4))
        decoded = huff_tree.decode(rom.data, ensure_file_offset(text_addr))
        messages.append(Message(decoded))
        print(
            "Loaded {:4d}/3403 messages...".format(i),
            end="\r",
            file=sys.stderr,
        )
    print(
        "Loaded 3403 messages.        ".format(i),
        file=sys.stderr,
    )
    return messages


def inject_messages(linker: Linker, messages: Iterable[Message], *, force_total_tree: bool = False):
    from . import linker as link_mod

    raw_msgs: List[bytes] = [msg.to_bytes() for msg in messages]

    # Construct and write out new Huffman tree
    huff_tree = HuffmanTree.build(raw_msgs, force_total=force_total_tree)
    huff_data = huff_tree.to_bytes()

    linker.add_section(
        "huffman",
        huff_data,
        {"gMsgHuffmanTable": 0, "gMsgHuffmanTableRootActual": len(huff_data) - 4},
    )
    huff_root_ptr = ensure_file_offset(linker.rom.read_int(0x6DC, 4))

    linker.add_rom_relocation(0x6E0, "gMsgHuffmanTable", relocation_types.OVERWRITE_32)
    linker.add_rom_relocation(
        huff_root_ptr, "gMsgHuffmanTableRootActual", relocation_types.OVERWRITE_32
    )

    # Encode and write message data
    encoder = huff_tree.get_encoder()
    msg_data = bytearray()
    msg_symbols = {}
    reloc_names = []
    for i, encoded in enumerate(map(encoder.encode, raw_msgs)):
        msg_symbols["__gMsgString_" + str(i)] = len(msg_data)
        reloc_names.append("__gMsgString_" + str(i))
        msg_data.extend(encoded)
    linker.add_section("strings", msg_data, msg_symbols)

    # Add a section for the string table
    table_section = linker.add_section("msgtab", bytearray(len(msg_symbols) * 4))
    linker.add_symbol(
        "gMsgStringTable",
        0,
        table_section,
        sym_type=link_mod.SYM_TYPE_DATA,
        size=len(table_section.data),
    )

    for i, sym_name in enumerate(reloc_names):
        linker.add_relocation(
            table_section, i * 4, sym_name, relocation_types.ABSOLUTE_32
        )

    # Add relocations within the ROM itself for the string table
    linker.add_rom_relocation(0xA26C, "gMsgStringTable", relocation_types.OVERWRITE_32)
    linker.add_rom_relocation(0xA2A0, "gMsgStringTable", relocation_types.OVERWRITE_32)


def save_messages(rom: ROMFile, messages: Iterable[Message], start_addr: int) -> int:
    raw_msgs: List[bytes] = [msg.to_bytes() for msg in messages]

    # Construct and write out new Huffman tree
    huff_tree = HuffmanTree.build(raw_msgs)
    tree_len = huff_tree.write_to_rom(rom, start_addr)
    print(
        "Wrote {} byte Huffman tree at {:08x}".format(tree_len, start_addr),
        file=sys.stderr,
    )

    # Encode and write message data
    encoder = huff_tree.get_encoder()
    cur_addr = start_addr + tree_len
    msg_addrs = []
    for encoded in map(encoder.encode, raw_msgs):
        msg_addrs.append(cur_addr)
        rom.write_bytes(encoded, cur_addr)
        cur_addr += len(encoded)

    print(
        "Wrote encoded messages to {:08x} - {:08x}".format(
            start_addr + tree_len, cur_addr
        ),
        file=sys.stderr,
    )

    # Write message pointer table
    msg_table_addr = (cur_addr & ~0x03) + 4  # align to 4 bytes
    cur_addr = msg_table_addr
    for msg_addr in msg_addrs:
        rom.write_addr(msg_addr, cur_addr)
        cur_addr += 4

    print("Wrote message table at {:08x}".format(msg_table_addr), file=sys.stderr)

    # Update references to message pointer table
    rom.write_addr(msg_table_addr, 0xA26C)
    rom.write_addr(msg_table_addr, 0xA2A0)

    return cur_addr
