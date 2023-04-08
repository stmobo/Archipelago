from __future__ import annotations

from typing import Dict, Iterator, List

from . import constants
from . import data_structs as structs
from .rom_file import ReadOnlyError, ROMFile
from .text import Message, load_messages


class ROM:
    file: ROMFile
    messages: List[Message]
    _characters: Dict[int, structs.CharacterData]
    _classes: Dict[int, structs.ClassData]
    _items: Dict[int, structs.ItemData]
    _immutable: bool

    def __init__(self, file: ROMFile, messages: List[Message], immutable: bool):
        self.file = file
        self.messages = messages
        self._characters = {}
        self._classes = {}
        self._items = {}
        self._immutable = immutable

    @property
    def immutable(self) -> bool:
        return self._immutable

    @classmethod
    def load(cls, data: bytes, immutable: bool) -> ROM:
        rom_file = ROMFile(data, immutable)
        messages = load_messages(rom_file)
        ret = cls(rom_file, messages, immutable)

        for id in constants.characters.PLAYABLE_CHARACTERS:
            ret._characters[id] = structs.CharacterData.load(ret, id)

        for id in constants.classes.PLAYABLE_CLASSES:
            ret._classes[id] = structs.ClassData.load(ret, id)

        for id in range(0x01, 0xCE):
            ret._items[id] = structs.ItemData.load(ret, id)

        return ret

    def clone(self, immutable: bool) -> ROM:
        new_rom = ROMFile(self.file.data)
        # new_rom.expand(0x2000000)
        new_messages = [Message(old_msg) for old_msg in self.messages]

        if immutable:
            new_rom.make_immutable()

        ret = ROM(new_rom, new_messages, immutable)

        for id in constants.characters.PLAYABLE_CHARACTERS:
            ret._characters[id] = structs.CharacterData.load(ret, id)

        for id in constants.classes.PLAYABLE_CLASSES:
            ret._classes[id] = structs.ClassData.load(ret, id)

        return ret

    def read_int(self, where: int, sz: int, *, signed=False) -> int:
        return self.file.read_int(where, sz, signed=signed)

    def write_int(self, value: int, where: int, sz: int, *, signed=False):
        if self.immutable:
            raise ReadOnlyError()
        self.file.write_int(value, where, sz, signed=signed)

    def read_bytes(self, where: int, sz: int) -> bytes:
        return self.file.read_bytes(where, sz)

    def read_byte_range(self, start: int, end: int) -> bytes:
        return self.file.read_byte_range(start, end)

    def write_bytes(self, value: bytes, where: int):
        if self.immutable:
            raise ReadOnlyError()
        self.file.write_bytes(value, where)

    def read_addr(self, where: int) -> int:
        return self.file.read_addr(where)

    def write_addr(self, value: int, where: int):
        if self.immutable:
            raise ReadOnlyError()
        return self.file.write_addr(value, where)

    def get_character(self, id: int) -> structs.CharacterData:
        if id not in self._characters:
            self._characters[id] = structs.CharacterData.load(self, id)
        return self._characters[id]

    def update_character(self, data: structs.CharacterData):
        if self.immutable:
            raise ReadOnlyError()
        self._characters[data.character_id] = data

    def get_class(self, id: int) -> structs.ClassData:
        if id not in self._classes:
            self._classes[id] = structs.ClassData.load(self, id)
        return self._classes[id]

    def update_class(self, data: structs.ClassData):
        if self.immutable:
            raise ReadOnlyError()
        self._classes[data.class_id] = data

    def get_item(self, id: int) -> structs.ItemData:
        if id not in self._items:
            self._items[id] = structs.ItemData.load(self, id)
        return self._items[id]

    def update_item(self, data: structs.ItemData):
        if self.immutable:
            raise ReadOnlyError()
        self._items[data.item_id] = data

    def get_message(self, id: int) -> Message:
        return self.messages[id]

    def playable_characters(self) -> Iterator[structs.CharacterData]:
        return map(self.get_character, constants.characters.PLAYABLE_CHARACTERS)

    def playable_classes(self) -> Iterator[structs.ClassData]:
        return map(self.get_class, constants.classes.PLAYABLE_CLASSES)

    def chapters(self) -> Iterator[structs.ChapterMetadata]:
        yield from structs.ChapterMetadata.load_all(self)

    def load_map_events(self) -> Iterator[structs.MapEvents]:
        for chapter in structs.ChapterMetadata.load_all(self):
            yield chapter.load_chapter_events()

    def load_world_map_nodes(self) -> Iterator[structs.WorldMapNode]:
        yield from structs.WorldMapNode.load_all(self)
