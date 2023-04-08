from __future__ import annotations

from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterable,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from .rom import ROM
from .rom_file import ensure_rom_address

_T = TypeVar("_T")


def __dataclass_transform__(
    *,
    eq_default: bool = True,
    order_default: bool = False,
    kw_only_default: bool = False,
    field_specifiers: tuple[type | Callable[..., Any], ...] = (()),
) -> Callable[[_T], _T]:
    return lambda a: a


class FrozenAttributeError(Exception):
    class_name: str
    attribute: str

    def __init__(self, class_name: str, attribute: str, *args: object) -> None:
        self.class_name = class_name
        self.attribute = attribute
        super().__init__(attribute, *args)

    def __str__(self) -> str:
        return "cannot change attribute {} of type {}".format(
            self.attribute, self.class_name
        )


def _validate_int_size(value: int, size: int, signed: bool, field_name: str):
    if not isinstance(value, int):
        raise TypeError(
            "field {} must be int (got {})".format(field_name, type(value).__name__)
        )

    n_bits = size * 8
    if signed:
        if value <= -(1 << (n_bits - 1)):
            raise ValueError(
                "value for {} exceeds minimum {}-bit value (got {})".format(
                    field_name, n_bits, value
                )
            )
        if value >= (1 << (n_bits - 1)):
            raise ValueError(
                "value for {} exceeds maximum signed {}-bit value (got {})".format(
                    field_name, n_bits, value
                )
            )
    else:
        if value < 0:
            raise ValueError(
                "value for {} cannot be negative (got {})".format(field_name, value)
            )
        if value >= (1 << n_bits):
            raise ValueError(
                "value for {} exceeds maximum sunigned {}-bit value (got {})".format(
                    field_name, n_bits, value
                )
            )


class Field:
    owner: type
    name: str
    offset: int
    size: int
    signed: bool

    def __init__(
        self,
        offset: int,
        size: int,
        signed: bool = False,
    ):
        self.owner = None
        self.name = None
        self.offset = offset
        self.size = size
        self.signed = signed

    @classmethod
    def u8(cls, offset: int) -> Field:
        return cls(offset, 1, False)

    @classmethod
    def u16(cls, offset: int) -> Field:
        return cls(offset, 2, False)

    @classmethod
    def u32(cls, offset: int) -> Field:
        return cls(offset, 4, False)

    @classmethod
    def i8(cls, offset: int) -> Field:
        return cls(offset, 1, True)

    @classmethod
    def i16(cls, offset: int) -> Field:
        return cls(offset, 2, True)

    @classmethod
    def i32(cls, offset: int) -> Field:
        return cls(offset, 4, True)

    def load(self, rom: ROM, base_address: int) -> int:
        return rom.read_int(base_address + self.offset, self.size, signed=self.signed)

    def save(self, rom: ROM, base_address: int, instance):
        rom.write_int(
            getattr(instance, "__" + self.name),
            base_address + self.offset,
            self.size,
            signed=self.signed,
        )

    def convert_and_validate(self, value: int) -> int:
        _validate_int_size(value, self.size, self.signed, self.full_name())
        return value

    def full_name(self) -> str:
        return self.owner.__name__ + "." + self.name

    def __set_name__(self, owner: type, name: str):
        self.owner = owner
        self.name = name

    def __get__(self, instance: Any, _owner: Optional[type] = None) -> int:
        if instance is None:
            return self
        else:
            return getattr(instance, "__" + self.name)

    def __set__(self, instance: Any, _value: int):
        raise FrozenAttributeError(type(instance).__name__, self.name)

    def __delete__(self, instance: Any, _value: int):
        raise FrozenAttributeError(type(instance).__name__, self.name)


class ArrayField:
    owner: type
    name: str
    offset: int
    elem_size: int
    length: int
    signed: bool

    def __init__(self, offset: int, elem_size: int, length: int, signed: bool = False):
        self.owner = None
        self.name = None
        self.offset = offset
        self.elem_size = elem_size
        self.length = length
        self.signed = signed

    @classmethod
    def u8(cls, offset: int, length: int) -> Field:
        return cls(offset, 1, length, signed=False)

    @classmethod
    def u16(cls, offset: int, length: int) -> Field:
        return cls(offset, 2, length, signed=False)

    @classmethod
    def u32(cls, offset: int, length: int) -> Field:
        return cls(offset, 4, length, signed=False)

    @classmethod
    def i8(cls, offset: int, length: int) -> Field:
        return cls(offset, 1, length, signed=True)

    @classmethod
    def i16(cls, offset: int, length: int) -> Field:
        return cls(offset, 2, length, signed=True)

    @classmethod
    def i32(cls, offset: int, length: int) -> Field:
        return cls(offset, 4, length, signed=True)

    def load(self, rom: ROM, base_address: int) -> Tuple[int, ...]:
        return tuple(
            rom.read_int(
                base_address + self.offset + (self.elem_size * i),
                self.elem_size,
                signed=self.signed,
            )
            for i in range(self.length)
        )

    def load_to_struct(self, rom: ROM, base_address: int, instance: Any):
        setattr(instance, "__" + self.name, self.load(rom, base_address))

    def save(self, rom: ROM, base_address: int, instance: Any):
        value = getattr(instance, "__" + self.name)
        if len(value) != self.length:
            raise ValueError(
                "data is of invalid length (got {}, expected {})".format(
                    len(value), self.length
                )
            )
        for i, elem in enumerate(value):
            rom.write_int(
                elem,
                base_address + self.offset + (self.elem_size * i),
                self.elem_size,
                signed=self.signed,
            )

    def convert_and_validate(self, value: Iterable[int]) -> Tuple[int, ...]:
        value = tuple(value)

        if len(value) != self.length:
            raise ValueError(
                "field {} must be length {} (got {})".format(
                    self.full_name(), self.length, len(value)
                )
            )

        for i, element in enumerate(value):
            _validate_int_size(
                element,
                self.elem_size,
                self.signed,
                "{}[{}]".format(self.full_name(), i),
            )

        return value

    def full_name(self) -> str:
        return self.owner.__name__ + "." + self.name

    def __set_name__(self, owner: type, name: str):
        self.owner = owner
        self.name = name

    def __get__(self, instance: Any, _owner: Optional[type] = None) -> int:
        if instance is None:
            return self
        else:
            return getattr(instance, "__" + self.name)

    def __set__(self, instance: Any, _value: int):
        raise FrozenAttributeError(type(instance).__name__, self.name)

    def __delete__(self, instance: Any, _value: int):
        raise FrozenAttributeError(type(instance).__name__, self.name)


class PointerField:
    owner: str
    name: str
    offset: int

    def __init__(self, offset: int):
        self.owner = None
        self.name = None
        self.offset = offset

    def load(self, rom: ROM, base_address: int) -> int:
        return rom.read_addr(base_address + self.offset)

    def load_to_struct(self, rom: ROM, base_address: int, instance: Any):
        setattr(instance, "__" + self.name, self.load(rom, base_address))

    def save(self, rom: ROM, base_address: int, instance: Any):
        value = getattr(instance, "__" + self.name)
        rom.write_addr(value, base_address + self.offset)

    def convert_and_validate(self, value: int) -> int:
        return ensure_rom_address(value)

    def full_name(self) -> str:
        return self.owner.__name__ + "." + self.name

    def __set_name__(self, owner: type, name: str):
        self.owner = owner
        self.name = name

    def __get__(self, instance: Any, _owner: Optional[type] = None) -> int:
        if instance is None:
            return self
        else:
            return getattr(instance, "__" + self.name)

    def __set__(self, instance: Any, _value: int):
        raise FrozenAttributeError(type(instance).__name__, self.name)

    def __delete__(self, instance: Any, _value: int):
        raise FrozenAttributeError(type(instance).__name__, self.name)


class StructAddress:
    owner: type
    name: str

    def __init__(self):
        self.owner = None
        self.name = None

    def convert_and_validate(self, value: int) -> int:
        return ensure_rom_address(value)

    def convert_from_address(self, addr: int) -> int:
        return ensure_rom_address(addr)

    def full_name(self) -> str:
        return self.owner.__name__ + "." + self.name

    def struct_address(self, addr: int) -> int:
        return ensure_rom_address(addr)

    def instance_struct_address(self, instance) -> int:
        return self.struct_address(getattr(instance, "__" + self.name))

    def __set_name__(self, owner: type, name: str):
        self.owner = owner
        self.name = name

    def __get__(self, instance: Any, _owner: Optional[type] = None) -> int:
        if instance is None:
            return self
        else:
            return getattr(instance, "__" + self.name)

    def __set__(self, instance: Any, _value: int):
        raise FrozenAttributeError(type(instance).__name__, self.name)

    def __delete__(self, instance: Any, _value: int):
        raise FrozenAttributeError(type(instance).__name__, self.name)


class StructID:
    owner_name: type
    name: str
    index_size: int
    base_address: int
    struct_size: int
    index_adjustment: int

    def __init__(
        self,
        *,
        index_size: int,
        base_address: int,
        struct_size: int,
        index_adjustment: int,
    ):
        self.owner = None
        self.name = None
        self.index_size = index_size
        self.base_address = base_address
        self.struct_size = struct_size
        self.index_adjustment = index_adjustment

    def convert_and_validate(self, value: int) -> int:
        _validate_int_size(value, self.index_size, False, self.full_name())
        return value

    def convert_from_address(self, addr: int) -> int:
        addr = ensure_rom_address(addr)
        offset = addr - self.base_address
        assert offset >= 0
        assert (offset % self.struct_size) == 0
        index = offset // self.struct_size
        return index - self.index_adjustment

    def struct_address(self, index: int) -> int:
        index += self.index_adjustment
        return self.base_address + (index * self.struct_size)

    def instance_struct_address(self, instance) -> int:
        return self.struct_address(getattr(instance, "__" + self.name))

    def full_name(self) -> str:
        return self.owner.__name__ + "." + self.name

    def __set_name__(self, owner: type, name: str):
        self.owner = owner
        self.name = name

    def __get__(self, instance, _owner: Optional[type] = None) -> int:
        if instance is None:
            return self
        else:
            return getattr(instance, "__" + self.name)

    def __set__(self, instance: Any, _value: int):
        raise FrozenAttributeError(type(instance).__name__, self.name)

    def __delete__(self, instance: Any, _value: int):
        raise FrozenAttributeError(type(instance).__name__, self.name)


class RomStruct:
    @classmethod
    def load(cls: Type[_T], rom: ROM, addr_or_idx: int, **kwargs) -> _T:
        raise NotImplementedError()

    def save(self: _T):
        raise NotImplementedError()

    def evolve(self: _T, **kwargs) -> _T:
        raise NotImplementedError()

    def with_rom(self: _T, rom: ROM) -> _T:
        return self.evolve(rom=rom)

    @property
    def struct_address(self) -> int:
        cls = type(self)
        address_field = None

        for val in cls.__dict__.values():
            if isinstance(val, StructAddress) or isinstance(val, StructID):
                if address_field is None:
                    address_field = val
                else:
                    raise ValueError(
                        "struct {} has multiple address fields".format(cls.__name__)
                    )
        return address_field.instance_struct_address(self)


@__dataclass_transform__(
    order_default=True,
    field_specifiers=(
        Field,
        Field.u8,
        Field.u16,
        Field.u32,
        Field.i8,
        Field.i16,
        Field.i32,
        ArrayField,
        ArrayField.u8,
        ArrayField.u16,
        ArrayField.u32,
        ArrayField.i8,
        ArrayField.i16,
        ArrayField.i32,
        PointerField,
        StructAddress,
        StructID,
    ),
)
def rom_struct(cls: Type[_T]) -> Type[_T]:
    fields: Dict[str, Union[Field, ArrayField, PointerField]] = {}
    address_field: Union[StructAddress, StructID] = None

    for name, val in cls.__dict__.items():
        if (
            isinstance(val, Field)
            or isinstance(val, ArrayField)
            or isinstance(val, PointerField)
        ):
            fields[name] = val
        elif isinstance(val, StructAddress) or isinstance(val, StructID):
            if address_field is None:
                address_field = val
            else:
                raise ValueError(
                    "struct {} has multiple address fields".format(cls.__name__)
                )

    if address_field is None:
        raise ValueError("struct {} has no address field".format(cls.__name__))

    def init_struct(instance: Any, rom: ROM, addr_src: int, **kwargs):
        nonlocal address_field, fields

        instance.rom = rom
        setattr(
            instance,
            "__" + address_field.name,
            address_field.convert_and_validate(addr_src),
        )

        for field in fields.values():
            try:
                val = kwargs[field.name]
            except KeyError:
                raise ValueError(
                    "missing required parameter {}".format(field.name)
                ) from None
            val = field.convert_and_validate(kwargs[field.name])
            setattr(instance, "__" + field.name, val)

        extra_kwargs = {}
        for name, val in kwargs.items():
            if name not in fields:
                extra_kwargs[name] = val
        setattr(instance, "__extra_init_kwargs", extra_kwargs)

        if "__post_init__" in type(instance).__dict__:
            type(instance).__dict__["__post_init__"](instance, rom, addr_src, **kwargs)

    def load_struct(rom: ROM, addr_src: int, **kwargs) -> cls:
        nonlocal address_field, fields, cls

        base_address = address_field.struct_address(addr_src)
        new_kwargs = kwargs
        for field in fields.values():
            new_kwargs[field.name] = field.load(rom, base_address)

        new_inst = object.__new__(cls)
        init_struct(new_inst, rom, addr_src, **new_kwargs)
        return new_inst

    def load_by_address(rom: ROM, addr: int, **kwargs) -> cls:
        nonlocal address_field
        addr_src = address_field.convert_from_address(addr)
        return load_struct(rom, addr_src, **kwargs)

    def save_struct(inst) -> cls:
        nonlocal address_field, fields

        rom = inst.rom
        base_address = address_field.instance_struct_address(inst)
        for field in fields.values():
            field.save(rom, base_address, inst)

        if "__post_save__" in type(inst).__dict__:
            type(inst).__dict__["__post_save__"](inst)

    def evolve_struct(inst, **kwargs) -> cls:
        nonlocal address_field, fields, cls

        rom = inst.rom
        if "rom" in kwargs:
            rom = kwargs["rom"]
            del kwargs["rom"]

        addr_src = getattr(inst, "__" + address_field.name)
        if address_field.name in kwargs:
            addr_src = kwargs[address_field.name]
            del kwargs[address_field.name]

        new_kwargs = {}
        new_kwargs.update(getattr(inst, "__extra_init_kwargs"))
        for field in fields.values():
            new_kwargs[field.name] = getattr(inst, "__" + field.name)
        new_kwargs.update(kwargs)

        new_inst = object.__new__(cls)
        init_struct(new_inst, rom, addr_src, **new_kwargs)
        return new_inst

    setattr(cls, "__init__", init_struct)
    setattr(cls, "load", load_struct)
    setattr(cls, "load_by_address", load_by_address)
    setattr(cls, "save", save_struct)
    setattr(cls, "evolve", evolve_struct)

    return cls
