# Copyright (c) 2023 MatrixEditor
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import annotations

__doc__ = """Abstract classes to support basic ABI implementations"""

import abc
import typing as t
import dataclasses as dc
import io

import lief
import construct as cs
import construct_dataclasses as csd

# Basic generic types will be annotated with this type variable
T = t.TypeVar("T")
StructTy = t.Union[t.Type[T], cs.Construct]

# Supported binary types
BinaryT = t.Union[lief.MachO.Binary, lief.PE.Binary]


def get_context_value(ctx, name: str):
    """Retrieve a context variable by its name (recursively).

    :param ctx: the context
    :type ctx: construct.Container
    :param name: the variable's name
    :type name: str
    :raises cs.ConstructError: if the variable could not be found
    :return: the associated value
    """
    root = ctx
    while name not in root:
        root = root._
        if root is None:
            raise cs.ConstructError(f"Invalid context: '{name}' missing")
    return root[name]


def __x64__(binary: BinaryT) -> bool:
    """Returns whether the binary is using 64-bit pointers

    :param binary: the parsed binary
    :type binary: BinaryT
    :return: whether the binary has 64-bit pointers
    :rtype: bool
    """
    header = binary.header
    if isinstance(header, lief.PE.Header):
        machine = header.machine
        types = lief.PE.MACHINE_TYPES
        return machine in (types.AMD64, types.ARM64, types.IA64)

    elif isinstance(header, lief.MachO.Header):
        cpu_type = header.cpu_type
        return cpu_type == lief.MachO.CPU_TYPES.ARM64


class DataStream(abc.ABC):
    """Dummy class used for type annotations.

    It should be used to parse construct classes based on their virtual
    address value. In addition every ``DataStream`` supports reading
    single or multiple raw bytes.
    """

    @abc.abstractmethod
    def read_struct(
        self, __struct: t.Generic[T], __vaddress: int, fix=False
    ) -> t.Optional[T]:
        """Reads a generic construct object or dataclass struct from the untderlying stream.

        :param __struct: the struct to parse
        :type __struct: t.Generic[T]
        :param __vaddress: the virtual memory address
        :type __vaddress: int
        :param fix: whether the address should be fixed, defaults to False
        :type fix: bool, optional
        :return: the parsed object or nothing in case of an error
        :rtype: t.Optional[T]
        """
        pass

    @abc.abstractmethod
    def read_raw(self, __vaddress: int, __size: int, fix=False) -> t.Optional[bytes]:
        """Reads raw bytes from the underlying stream.

        :param __vaddress: the virtual memory address
        :type __vaddress: int
        :param __size: the block size (how many bytes to consume)
        :type __size: int
        :param fix: whether the address should be translated before, defaults to False
        :type fix: bool, optional
        :return: the bytes read or none if an invalid virtual address was provided
        :rtype: t.Optional[bytes]
        """
        pass

    def __add__(self, struct: StructTy) -> VirtualMemoryBlock[T]:
        return VirtualMemoryBlock(self, struct)


@cs.singleton
class CString(cs.Construct):
    """
    A typing class that can be used to mark pointers to strings in virtual
    memory. Note that the returened string instance won't store the zero
    termination character at the end.
    """

    @staticmethod
    def is_cstring(ty) -> bool:
        """Returns whether the given object or type conforms to a ``CString``.

        :param ty: the object or type
        :type ty: type | CString
        :return: whether the given type conforms to a CString
        :rtype: bool
        """
        return type(ty) == type(CString) or ty == CString


@cs.singleton
class RawCString(cs.Construct):
    """
    A typing class that can be used to mark pointers to zero terminated
    bytearrays in virtual memory.
    """

    @staticmethod
    def is_raw_cstring(ty) -> bool:
        """Returns whether the given object or type conforms to a ``RawCString``.

        :param ty: the object or type
        :type ty: type | RawCString
        :return: whether the given type conforms to a RawCString
        :rtype: bool
        """
        return type(ty) == type(RawCString) or ty == RawCString


# This object represents an incomplete type that may be used within
# relative pointers (see Swift ABI)
Void = cs.Construct()

# Below are some common type aliases for struct definitions
int8_t = int
uint8_t = int
int16_t = int
uint16_t = int
int32_t = int
uint32_t = int
int64_t = int
uint64_t = int
uintptr_t = int


def _get_address(ctx) -> int:
    # Returns the address of the current context
    return get_context_value(ctx, "address")


def _get_data_stream(ctx) -> DataStream:
    # Returns the current data stream
    return get_context_value(ctx, "fp")


@dc.dataclass
class Virtual:
    """Base class of all virtual memory objects.

    Each runtime implementation should set the ``'address'`` and ``'fp'``
    variable in the base context before parsing any struct. It ensures
    that virtual memory objects store their address and datastream
    correctly.

    Example:

    >>> stream = ... # instance of DataStream
    >>> obj = stream.read_struct(Virtual, 12345)
    >>> obj._address
    12345
    """

    #: Using the root context to get the base address
    _address: int = csd.csfield(cs.Computed(_get_address))

    #: Using the root context to rerieve the internal memory stream (Instance of
    #: a Runtime class).
    _fp: DataStream = csd.csfield(cs.Computed(_get_data_stream))

    def __hash__(self) -> int:
        # Support for hashing of sub-classes
        return self._address


class VirtualArray(cs.Subconstruct):
    """Reimplementation of construct.Array that supports asigning virtual addresses."""

    def __init__(self, length, subcon):
        if dc.is_dataclass(subcon):
            # Small sanitization to support dataclass types in constructor
            subcon = csd.DataclassStruct(subcon)

        super().__init__(subcon)
        self.length = length

    def _sizeof(self, context, path):
        count = cs.evaluate(self.length, context)
        return self.subcon._sizeof(context, path) * count

    def _parse(self, stream, context, path):
        # Base address is always present when parsing via Runtime
        address = get_context_value(context, "address")
        values = []
        size = sizeof(self.subcon)

        count = cs.evaluate(self.length, context)
        for _ in range(count):
            # As the subcon extends from Virtual, we have to place the
            # address into the current context
            context.address = address
            obj = self.subcon._parse(stream, context, path)
            values.append(obj)
            address += size

        return values


class AlignedUnion(cs.Adapter):
    """Wrapper around construct's ``Union`` class that supports a size.

    Parsing first parses the union and then consumes the amount of bytes
    specified in the length of this struct.
    """

    def __init__(self, length, subcon: cs.Construct):
        super().__init__(subcon)
        self.length = length

    def _parse(self, stream, context, path):
        obj = super()._parse(stream, context, path)
        length = cs.evaluate(self.length, context)
        # We have to 'consume' the parsed bytes because Union doesn't do that.
        cs.stream_seek(stream, cs.stream_tell(stream, path) + length, 0, path)
        return obj

    def _decode(self, obj, context, path):
        # Just return the parsed union
        return obj

    def _encode(self, obj, context, path):
        # the union will work on that object later on
        return obj

    def _sizeof(self, context, path):
        # Using cs.evaluate we can compute the size of this struct
        return cs.evaluate(self.length, context) or 0


def sizeof(__struct: t.Union[cs.Construct, dc._DataclassT], **contextkw) -> int:
    """Computes the size of a Construct object or dataclass struct.

    :param __struct: the struct or dataclass type
    :type __struct: t.Union[cs.Construct, dc._DataclassT]
    :return: the struct's size
    :rtype: int
    """
    if dc.is_dataclass(__struct):
        struct = csd.DataclassStruct(__struct)
        return struct.sizeof(**contextkw)

    return __struct.sizeof(**contextkw)


class VirtualMemoryBlock(t.Generic[T]):
    """A virtual memory block that can be used to parse struct at certain addresses.

    This class can be used in 'with' statements and supports the '@' operation to
    parse the structs:

    >>> with VirtualMemoryBlock(runtime) as block:
    ...     obj = (block+StructClass) @ 0x1234
    ...

    The '+' operation is used to assign a struct type to this memory block and '@'
    finally to parse it. The shortcut for the code above would be:

    >>> obj = (runtime+StructClass) @ 0x1234
    """

    #: the datastream
    stream: DataStream
    #: the dataclass or construct to parse
    struct: StructTy

    def __init__(self, stream, struct=None) -> None:
        self.stream = stream
        self.struct = struct

    def __matmul__(self, address: int) -> T:
        return self.stream.read_struct(self.struct, address)

    def __repr__(self) -> str:
        if isinstance(self.struct, type):
            name = self.struct.__name__
        else:
            name = type(self.struct).__name__
        return f"<{self.stream.__class__.__name__}+{name}>"

    def __add__(self, struct) -> VirtualMemoryBlock:
        return VirtualMemoryBlock(self.stream, struct)

    def __enter__(self) -> t.Self:
        return self

    def __exit__(self, exx_type, exc_value, traceback) -> None:
        pass  # ignore errors


class Runtime(DataStream):
    """Basic implementation of a :class:`DataStream`.

    Each ABI implementation should extend this class as it provides basic functionality
    when parsing structs or strings. In addition, there is an inbuilt cache that returns
    its values on requested virtual addresses. This class provides the following methods
    as its public API:

    - ``read_struct``: parsing structs
    - ``read_raw``: reading raw data blocks
    - ``read_string``: parsing of zero-terminated strings
    - ``read_ptr_section``: parsing a whole section as pointers
    - ``read_terminated``: abstract parsing of terminated sequences

    :param __binary: the parsed binary
    :type __binary: BinaryT
    """

    def __init__(self, __binary: BinaryT) -> None:
        self._binary = __binary
        # internal cache to reduce redundant parsing
        self._cache: t.Dict[tuple, t.Any] = {}

    def __repr__(self) -> str:
        # REVISIT: maybe include more information here
        is_64 = "x64" if self.is_64() else "x32"
        return f"<{self.__class__.__name__} {is_64}>"

    @property
    def binary(self) -> BinaryT:
        """Returns the parsed binary."""
        return self._binary

    def get_binary_kind(self) -> str:
        """Returns the module name for the parsed binary.

        :return: the binary's module name
        :rtype: str
        """
        name = self.binary.__module__
        # Small script to get the module name
        return name.split(".")[-1].lower()

    def fixup_address(self, __vaddress: int) -> int:
        """Transforms the given virtual address.

        Some virtual addresses contain extra information that should be emitted.
        Therefore, sub-classes may implement this function to remove that
        information.

        :param __vaddress: the virtual memory address
        :type __vaddress: int
        :return: the 'fixed' address
        :rtype: int
        """
        return __vaddress

    def is_64(self) -> bool:
        """Returns whether this runtime is using 64-bit structures

        :return: whether the underlying binary uses 64-bit
        :rtype: bool
        """
        return __x64__(self.binary)

    # Implementation of DataStream
    def read_struct(
        self, __struct: t.Generic[T], __vaddress: int, /, fix=False
    ) -> t.Optional[T]:
        """Parses the given struct at the provided virtual address.

        This method not only accepts construct objects, it also supports raw
        dataclass types. For example, the follwing class is defined to be
        a dataclass stuct:

        >>> @dataclass
        ... class Foo:
        ...     value: int = csfield(Int32ul)
        ...

        with an object extending the ``Runtime`` class, you can use a raw type
        reference to parse the virtual memory.

        >>> runtime = ... # assume your instance here
        >>> runtime.read_struct(Foo, 0x12345)
        Foo(value=...)

        Note that the usage of ``CString`` will result in a returned string value
        and ``RawString`` will return the string as a bytearray (``bytes`` object).

        :param __struct: the struct to parse
        :type __struct: dataclass type reference or Construct instance
        :param __vaddress: the virtual memory address
        :type __vaddress: int
        :param fix: whether to fix the provided address, defaults to False
        :type fix: bool, optional
        :return: the parsed struct or nothing on an invalid address
        :rtype: t.Optional[T]
        """

        # Fix the incoming address if nexessary
        vaddress = self.fixup_address(__vaddress) if fix else __vaddress
        if CString.is_cstring(__struct):
            # Use cstring method to parse terminated strings
            return self.read_string(vaddress)
        elif RawCString.is_raw_cstring(__struct):
            # This will return the cstring bytes instead of its
            # decoded string value
            return self.read_terminated(vaddress)

        model = __struct
        if isinstance(__struct, csd.DataclassStruct):
            model = __struct.model

        cached = self._cache.get((vaddress, model))
        if cached is not None:
            return cached

        if dc.is_dataclass(__struct):
            struct = csd.DataclassStruct(__struct)
        else:
            struct = __struct

        data = self.read_raw(vaddress, sizeof(struct, fp=self))
        if data is not None:
            result = struct.parse(data, address=vaddress, fp=self)
            self._cache[(vaddress, model)] = result
            return result

    def read_raw(self, __vaddress: int, __size: int, /, fix=False) -> t.Optional[bytes]:
        """Reads the data from the provided virtual address

        :param __vaddress: the virtual starting address
        :type __vaddress: int
        :param __size: the amount of bytes to read
        :type __size: int
        :param fix: whether to fix the virtual address, defaults to False
        :type fix: bool, optional
        :return: the bytes consumed
        :rtype: t.Optional[bytes]
        """
        assert __vaddress >= 0, "Invalid negative virtual address"

        # Fix the incoming address if nexessary
        vaddress = self.fixup_address(__vaddress) if fix else __vaddress

        try:
            if not self.binary.section_from_virtual_address(__vaddress):
                # Don't include invalid addresses
                return
        except AttributeError:
            pass

        # Invalid virtual memory addresses result in negative size
        # memory mappings
        data = self.binary.get_content_from_virtual_address(vaddress, __size)
        if data.nbytes >= 0:
            return bytes(data)

    # Additional utility methods
    def read_terminated(self, __vaddress: int, term=0, fix=False) -> t.Optional[bytes]:
        """Parses a terminated byte sequence using a 16-byte buffer.

        :param __vaddress: the starting address
        :type __vaddress: int
        :param term: the terminator, defaults to 0
        :type term: int, optional
        :param fix: whether to apply a fix the given address, defaults to False
        :type fix: bool, optional
        :return: the consumed bytes excluding the terminator
        :rtype: t.Optional[bytes]
        """
        assert __vaddress >= 0, "Invalid negative virtual address"
        assert term >= 0, "Invalid negative terminator"

        values = []
        max_len = 16
        terminated = False

        # Fix the incoming address if nexessary
        vaddress = self.fixup_address(__vaddress) if fix else __vaddress
        # Simple and small algorithm to parse terminated data
        while not terminated:
            chars = self.read_raw(vaddress, max_len)
            # stop this loop if there is no data left
            if chars is None:
                break

            for ch in chars:
                if ch == term:
                    terminated = True
                    break
                # The terminated value won't be included in the returned array
                values.append(ch)

            if not terminated:
                vaddress += max_len

        return bytes(values)

    def read_string(self, __vaddress: int, fix=False) -> t.Optional[str]:
        """Parses a CString without the trailing zero.

        :param __vaddress: the starting address
        :type __vaddress: int
        :param fix: whether to fix the address, defaults to False
        :type fix: bool, optional
        :return: the parsed string or nothing on failure
        :rtype: t.Optional[str]
        """
        data = self.read_terminated(__vaddress, fix=fix)
        try:
            # REVISIT: Maybe support unicode literals.
            return data.decode()
        except (UnicodeDecodeError, AttributeError):
            # We have to include the attribute error as NoneType
            # may be returned as well
            pass

    def read_ptr_section(
        self, __name: str, struct: t.Optional[cs.Construct] = None
    ) -> t.Dict[int, int]:
        """Parses a pointer section (see :class:`ReflectionSectionIterator`)

        :param __name: the section's name
        :type __name: str
        :param struct: the pointer struct, defaults to None
        :type struct: t.Optional[cs.Construct], optional (default is Int64ul)
        :return: the pointer values mapped to their virtual address
        :rtype: t.Dict[int, int]
        """
        section = self.binary.get_section(__name)
        if section is None:
            # This function should not return any null values
            return {}

        # Address to pointer mapping
        a2p_map = {}

        # Basic section information used to iterator over its content
        base = section.virtual_address
        data = section.content

        struct = struct or cs.Int64ul
        word_size = sizeof(struct, fp=self)

        size = getattr(section, "virtual_size", section.size)
        num_ptrs = int(size / word_size)
        ptr_offset = 0

        for _ in range(num_ptrs):
            # the returned dictionary will store the virtual address of the pointer
            # and its value
            location = int(base + ptr_offset)
            data_end = ptr_offset + word_size

            value = struct.parse(data[ptr_offset:data_end])
            # never forget to increment the offset at the end
            ptr_offset += word_size

            if value == 0:
                # NOTE: some PEs may include extra padding at the start of each section.
                # We will ignore that.
                continue

            a2p_map[location] = value

        return a2p_map

    def pointers(
        self, __name: str, struct: t.Optional[cs.Construct] = None
    ) -> t.List[int]:
        """Returns only the values of all pointers

        :param __name: the section's name
        :type __name: str
        :param struct: the pointer struct to use, defaults to None
        :type struct: t.Optional[cs.Construct], optional
        :return: a list of parsed pointer values
        :rtype: t.List[int]
        """
        ptrs = self.read_ptr_section(__name, struct=struct)
        return list(ptrs.values())


class BinaryFile(DataStream):
    """Minimal implementation of :class:`DataStream` to support single-file operations."""

    def __init__(self, __stream: str) -> None:
        self._stream = __stream
        self._size = cs.stream_size(__stream)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} size={self.size}>"

    @property
    def stream(self) -> io.IOBase:
        return self._stream

    @property
    def size(self) -> int:
        return self._size

    # Implementation of DataStream
    def read_raw(self, __vaddress: int, __size: int, /, fix=False) -> bytes:
        assert __vaddress >= 0, "Invalid negative virtual address"
        assert __vaddress + __size < self.size, "Range to read exceeds file size!"

        # parameter 'fix' will be ignored here
        self.stream.seek(__vaddress)
        return self.stream.read(__size)

    def read_struct(
        self, __struct: t.Generic[T], __vaddress: int, /, fix=False
    ) -> t.Optional[T]:
        # 'fix' parameter also ingored here:
        vaddress = __vaddress
        if CString.is_cstring(__struct):
            # Use cstring method to parse terminated strings
            return self.read_string(vaddress)
        elif RawCString.is_raw_cstring(__struct):
            # This will return the cstring bytes instead of its
            # decoded string value
            return self.read_terminated(vaddress)

        if dc.is_dataclass(__struct):
            struct = csd.DataclassStruct(__struct)
        else:
            struct = __struct

        self.stream.seek(vaddress)
        return struct.parse_stream(self.stream, address=vaddress, fp=self)

    # Some other utility methods
    def read_terminated(self, __vaddress: int, term=0) -> bytes:
        assert __vaddress >= 0, "Invalid negative virtual address"
        assert term >= 0, "Invalid negative terminator"

        data = []
        self.stream.seek(__vaddress)
        while True:
            ch = cs.stream_read(self.stream, 1, "(parsing) -> terminated")
            if ch == term:
                break
            data.append(ch)

        return bytes(data)

    def read_string(self, __vaddress: int) -> t.Optional[str]:
        try:
            return self.read_terminated(__vaddress).decode()
        except (cs.StreamError, UnicodeDecodeError):
            pass
