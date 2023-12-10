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

import typing as t

import dataclasses as dc
import construct as cs
import construct_dataclasses as csd

from inspect import isfunction

from umbrella.runtime import DataStream, get_context_value, Runtime


# Apply a relative offset to a base pointer.
def applyRelativeOffset(__base_address: int, __offset: int) -> int:
    return __base_address + __offset


# Measure the relative offset between two pointers.
def measureRelativeOffset(__referent: int, __base: int) -> int:
    return __referent - __base


# REVISIT: maybe ship this method to a "utils" section
def _get_struct(value_ty) -> cs.Construct:
    if isfunction(value_ty):
        value_ty = value_ty()

    if isinstance(value_ty, cs.Construct):
        return value_ty
    elif dc.is_dataclass(value_ty):
        return csd.DataclassStruct(value_ty)
    else:
        raise TypeError(f"Unknown struct type - {value_ty}")


# Basic value and pointee type variables
ValueTy = t.TypeVar("ValueTy")
PointeeTy = t.TypeVar("PointeeTy")

# The following types can be used within a pointer type annotation
# to indicate a pointer may be null. It is recommended to use these
# types rather than plain True or False.
Nullable = t.Type[bool]
NotNull = t.Type[bool]
NullableTy = t.TypeVar("NullableTy", Nullable, NotNull)


# Actual value types can be represented through both, dataclass types
# and construct objects
ValueT = t.Union[t.Type[ValueTy], cs.Construct, t.Callable[[], ValueTy]]
IndirectT = t.Union[t.Type[ValueTy], cs.Construct]
PointeeT = t.Union[t.Type[PointeeTy], cs.Construct]
IntTy = t.TypeVar("IntTy", bound=cs.Construct)


class DirectPointer(cs.Construct, t.Generic[ValueTy, NullableTy]):
    """Direct pointer to a virtual struct.

    Pointers of this type are platform-specific length pointers. For example,
    arm64 binaries will take a 64-bit pointer and default arm binaries only
    32-bit. In order to address this issue, this pointer class implements a
    mechanism to automatically use the right pointer size based on the binary's
    architecture.

    >>> ptr = DirectPointer(Void)
    >>> sizeof(ptr, fp=Runtime(binary_x64))
    8
    >>> sizeof(ptr, fp=Runtime(binary_x32))
    4

    The value, associated with this pointer can be retrieved by simply calling
    ``get``.

    >>> ptr = DirectPointer(CString)
    >>> ptr.offset = 0x12345
    >>> ptr.get(fp=Runtime(binary_x64))
    'foo'

    .. note::
        This pointer can be used within type annotation as well. It takes two
        type arguments:

        1. _ValueTy_: the struct type
        2. _NullableTy_: whether the pointer is nullable

        Example:
        >>> class Foo:
        ...     ptr: DirectPointer[CString, NotNull] = ...
        ...

    :param value_ty: the actual value type - can by dataclass type, construct
                     instance or lambda that returns either one of those.
    :type value_ty: ValueT
    :param nullable: whether this pointer can be null, defaults to False
    :type nullable: bool, optional
    """

    offset: int  # the actual value
    nullable: bool  # whether this pointer can be null

    # The runtime object used to parse the underlying struct
    _fp: DataStream

    # Stores the current struct instance (internal attribute)
    _struct: cs.Construct

    # Stores the internal value type (can be Construct or type reference)
    _value_ty: ValueT

    def __init__(self, value_ty: ValueT, nullable: bool = False):
        super().__init__()
        self.nullable = nullable
        self.offset = 0
        # Internal attributes
        self._value_ty = value_ty
        self._fp = None
        self._struct = None

    def is_null(self) -> bool:
        """Returns whether this pointer is null ( zero value ).

        :return: true if the offset is zero
        :rtype: bool
        """
        return self.offset == 0

    def get_struct(self) -> cs.Construct:
        """Returns (or creates) the construct of the value type.

        :return: returns the construct representation
        :rtype: cs.Construct
        """
        if self._struct is None:
            # lazy creation, because value_ty may be a lambda
            self._struct = _get_struct(self._value_ty)
        return self._struct

    def get(self, fp: DataStream = None) -> t.Optional[ValueTy]:
        """
        Parses the underlying struct using the internal or provided data stream.

        :param fp: the data stream, defaults to None
        :type fp: DataStream, optional
        :return: the parsed struct or nothing if this pointer is null
        :rtype: t.Optional[ValueTy]
        """
        if self.is_null():
            if not self.nullable:
                raise ValueError("NotNull pointer is null!")
            # Just return nothing
            return None

        fp = fp or self._fp
        ref_address = self.offset
        # This enables us lazy creation of construct objects
        struct = self.get_struct()
        return fp.read_struct(struct, ref_address)

    def _parse(self, stream, context, path):
        # Measure the platform first we decide which pointer size should be
        # read based on it.
        fp = get_context_value(context, "fp")
        assert isinstance(
            fp, Runtime
        ), "Invalid data stream detected - expected a runtime instance"

        struct = cs.Int64ul if fp.is_64() else cs.Int32ul
        value: int = struct._parse(stream, context, path)

        # Create a new pointer instance. This is necessary, because we can't store
        # the value in a global DirectPointer instance.
        ptr = DirectPointer(self._value_ty, self.nullable)
        ptr._fp = fp
        self.offset = value
        return ptr

    def _sizeof(self, context, path):
        # Calculates the size of this struct. This will fail if the data stream
        # has not been set within the sizeof(...) call
        fp = get_context_value(context, "fp")
        struct = cs.Int64ul if fp.is_64() else cs.Int32ul
        return struct._sizeof(context, path)

    def __repr__(self):
        return f"<{type(self.value_ty).__name__} at {self.offset:#x}>"


class RelativeDirectPointer(cs.Adapter, t.Generic[ValueTy, NullableTy]):
    """Relative pointer to a struct in virtual memory.

    This class represents a platform independent relative pointer to a struct in
    the virtual memory section. Swift uses signed integers to point to actual
    structs in memory based on the current address.

    >>> location = address + relative_offset

    :param value_ty: the actual value type - can by dataclass type, construct
                     instance or lambda that returns either one of those.
    :type value_ty: ValueT
    :param nullable: whether this pointer can be null, defaults to False
    :type nullable: bool, optional
    """

    relative_offset: int  # signed integer
    nullable: bool  # whether this pointer can be null

    _value_ty: ValueT  # referenced value type
    _fp: DataStream  # the used data stream after parsing
    _struct: cs.Construct  # the cached construct instance

    def __init__(self, value_ty: ValueT, nullable: bool = False):
        super().__init__(cs.Int32sl)
        self.nullable = nullable
        self.relative_offset = 0
        # internal attributes
        self._value_ty = value_ty
        self._struct = None
        self._fp = None

    def is_null(self) -> bool:
        """Returns whether this pointer is null ( zero value ).

        :return: true if the offset is zero
        :rtype: bool
        """
        return self.relative_offset == 0

    def get_struct(self) -> cs.Construct:
        """Returns (or creates) the construct of the value type.

        :return: returns the construct representation
        :rtype: cs.Construct
        """
        if self._struct is None:
            # lazy creation, because value_ty may be a lambda
            self._struct = _get_struct(self._value_ty)
        return self._struct

    def get(self, __base: int, fp: DataStream = None) -> t.Optional[ValueTy]:
        """
        Parses the underlying struct using the internal or provided data stream.

        :param __base: the base address
        :type __base: int
        :param fp: the data stream, defaults to None
        :type fp: DataStream, optional
        :return: the parsed struct or nothing if this pointer is null
        :rtype: t.Optional[ValueTy]
        """
        if self.is_null():
            if not self.nullable:
                raise ValueError("NotNull pointer is null!")
            # Just return nothing
            return None

        fp = fp or self._fp
        ref_address = applyRelativeOffset(__base, self.relative_offset)
        struct = self.get_struct()  # lazy creation of the struct
        return fp.read_struct(struct, ref_address)

    def _decode(self, obj, context, path) -> RelativeDirectPointer[ValueTy, NullableTy]:
        fp = get_context_value(context, "fp")
        assert isinstance(
            fp, Runtime
        ), "Invalid data stream detected - expected a runtime instance"

        # Create a new pointer instance. This is necessary, because we can't store
        # the value in a global instance. Using type(self) ensures the right pointer
        # class.
        ptr = type(self)(self._value_ty, self.nullable)
        ptr._fp = fp
        ptr.relative_offset = obj
        return ptr

    def __repr__(self):
        return f"<{self.__class__.__name__} at offset {self.relative_offset:#x}>"


# As defined within TargetLayout.h
#
# using CompactFunctionPointer =
#       swift::RelativeDirectPointer<T, Nullable, Offset>;
#
CompactFunctionPointer = RelativeDirectPointer


class RelativeIndirectPointer(RelativeDirectPointer[ValueTy, NullableTy]):
    """A relative (indirect) reference to an object stored in virtual memory.

    The ``get`` method first tries to read a pointer at the offset position and
    then parses the actual struct based on the pointer's value.

    :param value_ty: the actual value type - can by dataclass type, construct
                    instance or lambda that returns either one of those.
    :type value_ty: ValueT
    :param nullable: whether this pointer can be null, defaults to False
    :type nullable: bool, optional
    """

    def get(self, __base: int, fp: DataStream = None) -> t.Optional[ValueTy]:
        if self.is_null():
            if not self.nullable:
                raise ValueError("NotNull pointer is null!")
            # Just return nothing
            return None

        ref_address = applyRelativeOffset(__base, self.relative_offset)
        struct = self.get_struct()

        fp = self._fp or fp
        # Adjust the pointer size based on the current platform
        ptr_struct = cs.Int64ul if fp.is_64() else cs.Int32ul
        address: int = fp.read_struct(ptr_struct, ref_address)
        if not address:
            if self.nullable:
                return None
            raise ValueError(f"Invalid pointer address: {address:#x}")

        # Parse the struct at the right address
        return fp.read_struct(struct, address)


class RelativeIndirectablePointer(RelativeIndirectPointer[ValueTy, NullableTy]):
    """
    A relative reference to an object stored in virtual memory. The reference
    may be direct or indirect, and uses the low bit of the (assumed at least
    2-byte-aligned) pointer to differentiate.

    :param RelativeIndirectPointer: _description_
    :type RelativeIndirectPointer: _type_
    :raises ValueError: _description_
    :return: _description_
    :rtype: _type_
    """

    # referenced indirect type
    _indirect_ty: ValueT

    # indirect struct reference
    _indirect_struct: cs.Construct

    def __init__(
        self, value_ty: ValueT, nullable: bool = False, indirect_ty: ValueT = None
    ):
        super().__init__(value_ty, nullable)
        self._indirect_struct = None
        self._indirect_ty = indirect_ty or value_ty

    def get_indirect_struct(self) -> cs.Construct:
        """Returns (or creates) the construct of the indirect value type.

        :return: returns the construct representation
        :rtype: cs.Construct
        """
        if self._indirect_struct is None:
            # lazy creation, because value_ty may be a lambda
            self._struct = _get_struct(self._indirect_ty)
        return self._indirect_struct

    def get(self, __base: int, fp: DataStream = None) -> t.Optional[ValueTy]:
        if self.is_null():
            if not self.nullable:
                raise ValueError("NotNull pointer is null!")
            # Just return nothing
            return None

        fp = self._fp or fp
        offset = self.relative_offset & ~1
        ref_address = applyRelativeOffset(__base, offset)

        # If the low bit is set, then this is an indirect address. Otherwise,
        # it's direct.
        if self.relative_offset & 1:
            ptr_struct = DirectPointer(self._indirect_ty, self.nullable)
            ptr: DirectPointer = fp.read_struct(ptr_struct, ref_address)
            return ptr.get()

        return fp.read_struct(self.get_struct(), ref_address)

    def _decode(
        self, obj, context, path
    ) -> RelativeIndirectablePointer[ValueTy, NullableTy]:
        # As we have an additional constructor argument, we need a new
        # implementation of this method
        ptr = RelativeIndirectablePointer(
            self._value_ty, self.nullable, self._indirect_ty
        )
        ptr._fp = get_context_value(context, "fp")
        ptr.relative_offset = obj
        return ptr


class RelativeDirectPointerIntPair(RelativeDirectPointer[PointeeTy, NullableTy]):
    """
    A direct relative reference to an aligned object, with an additional
    tiny integer value crammed into its low bits.
    """

    _int_ty: IntTy  #! referenced int type

    def __init__(
        self, value_ty: PointeeTy, nullable: bool = False, int_ty: IntTy = cs.Byte
    ):
        super().__init__(value_ty, nullable)
        self._int_ty = int_ty

    def get_mask(self) -> int:
        return _get_struct(self._int_ty).sizeof() - 1

    def get_int(self) -> int:
        return self.get_mask() & self.relative_offset

    def _decode(
        self, obj, context, path
    ) -> RelativeDirectPointerIntPair[PointeeTy, NullableTy]:
        ptr = RelativeDirectPointerIntPair(self._value_ty, self.nullable, self._int_ty)
        ptr._fp = get_context_value(context, "fp")
        ptr.relative_offset = obj
        return ptr


class RelativeIndirectablePointerIntPair(
    RelativeIndirectablePointer[PointeeTy, NullableTy]
):
    """A relative reference to an aligned object stored in memory.

    The reference may be direct or indirect, and uses the low bit of the (assumed
    at least 2-byte-aligned) pointer to differentiate. The remaining low bits store
    an additional tiny integer value.
    """

    _int_ty: IntTy  #! referenced int type

    def __init__(
        self,
        value_ty: ValueT,
        nullable: bool = False,
        indirect_ty: ValueT = None,
        int_ty: IntTy = cs.Byte,
    ):
        super().__init__(value_ty, nullable, indirect_ty)
        self._int_ty = int_ty

    def get_mask(self) -> int:
        return (_get_struct(self._int_ty).sizeof() - 1) & ~1

    def get_unresolved_offset(self) -> int:
        return self.relative_offset & ~self.get_mask()

    def get_int(self) -> int:
        return (self.get_mask() & self.relative_offset) >> 1

    def _decode(
        self, obj, context, path
    ) -> RelativeIndirectablePointerIntPair[PointeeTy, NullableTy]:
        ptr = RelativeIndirectablePointerIntPair(
            self._value_ty, self.nullable, self._indirect_ty, self._int_ty
        )
        ptr._fp = get_context_value(context, "fp")
        ptr.relative_offset = obj
        return ptr

    def get(self, __base: int, fp: DataStream = None) -> t.Optional[ValueTy]:
        if self.is_null():
            if not self.nullable:
                raise ValueError("NotNull pointer is null!")
            # Just return nothing
            return None

        fp = self._fp or fp
        offset = self.get_unresolved_offset()
        ref_address = applyRelativeOffset(__base, offset)

        # If the low bit is set, then this is an indirect address. Otherwise,
        # it's direct.
        if self.relative_offset & 1:
            ptr_struct = DirectPointer(self._indirect_ty, self.nullable)
            ptr: DirectPointer = fp.read_struct(ptr_struct, ref_address)
            return ptr.get()

        return fp.read_struct(self.get_struct(), ref_address)
