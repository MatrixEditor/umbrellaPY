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

import dataclasses as dc
import typing as t

import construct as cs
import construct_dataclasses as csd

from umbrella.runtime import Virtual, uint32_t, uint64_t, int32_t, uintptr_t, uint16_t
from umbrella.objc import Pointer64, Pointer32


@dc.dataclass
class TargetMethodRaw64(Virtual):
    """Objective-C method description."""

    #: The name of this method.
    name: uintptr_t = csd.csfield(Pointer64)
    #: The types of this method.
    signature: uintptr_t = csd.csfield(Pointer64)
    #: The absolute implementation address
    impl: uintptr_t = csd.csfield(Pointer64)


@dc.dataclass
class TargetMethodRaw32(Virtual):
    # The name of this method.
    name: uintptr_t = csd.csfield(Pointer32)
    # The types of this method.
    signature: uintptr_t = csd.csfield(Pointer32)
    impl: uintptr_t = csd.csfield(Pointer32)


@dc.dataclass
class TargetSmallMethodRaw(Virtual):
    # The name of this method.
    name: int32_t = csd.csfield(cs.Int32sl)
    # The types of this method.
    signature: int32_t = csd.csfield(cs.Int32sl)
    impl: int32_t = csd.csfield(cs.Int32sl)


@dc.dataclass
class TargetIVarRaw64(Virtual):
    """Raw IVar structure."""

    #: offset was originally 64-bit on some x86_64 platforms.
    #: We read and write only 32 bits of it. Some metadata provides all 64
    #: bits. This is harmless for unsigned little-endian values.
    offset: int32_t = csd.csfield(cs.Int32sl)
    remainder: uint32_t = csd.csfield(cs.Int32ul)  #: unused (only 64-bit)
    name: uintptr_t = csd.csfield(Pointer64)  #: the name of this ivar
    type: uintptr_t = csd.csfield(Pointer64)  #: its type
    alignment: uint32_t = csd.csfield(cs.Int32ul)  #: the internal alignment
    size: uint32_t = csd.csfield(cs.Int32ul)  #: the internal ivar size in memory


@dc.dataclass
class TargetIVarRaw32(Virtual):
    offset: int32_t = csd.csfield(cs.Int32sl)
    name: uintptr_t = csd.csfield(Pointer32)
    type: uintptr_t = csd.csfield(Pointer32)
    alignment: uint32_t = csd.csfield(cs.Int32ul)
    size: uint32_t = csd.csfield(cs.Int32ul)


@dc.dataclass
class TargetPropertyRaw64(Virtual):
    """Raw layout of an Objective-C property."""

    name: uintptr_t = csd.csfield(Pointer64)  #: the property's name (reference)
    attributes: uintptr_t = csd.csfield(Pointer64)  #: its attributes (reference)


@dc.dataclass
class TargetPropertyRaw32(Virtual):
    name: uintptr_t = csd.csfield(Pointer32)
    attributes: uintptr_t = csd.csfield(Pointer32)


@dc.dataclass
class TargetGenericList(Virtual):
    # high bits used for fixup markers
    entsize_and_flags: uint32_t = csd.csfield(cs.Int32ul)
    count: uint32_t = csd.csfield(cs.Int32ul)

    def get_mask(self) -> int:
        return getattr(self, "mask", 0)

    def entsize(self) -> int:
        return self.entsize_and_flags & ~self.get_mask()

    def flags(self) -> int:
        return self.entsize_and_flags & self.get_mask()


@dc.dataclass
class TargetMethodList(TargetGenericList):
    mask: int = csd.csfield(cs.Computed(lambda _: 0xFFFF0003))


TargetIVarList = TargetGenericList
TargetPropertyList = TargetGenericList


@dc.dataclass
class TargetObjCObjectRaw64(Virtual):
    """Base struct for all definitions that may store a class definition."""

    isa_storage: uintptr_t = csd.csfield(Pointer64)
    """Class storage or pointer"""


@dc.dataclass
class TargetObjCObjectRaw32(Virtual):
    # Class storage or pointer
    isa_storage: uintptr_t = csd.csfield(Pointer32)


@dc.dataclass
class TargetProtocolRaw64(TargetObjCObjectRaw64):
    """Raw protocol struct."""

    #: the protocol's name (reference)
    name: uintptr_t = csd.csfield(Pointer64)
    #: a reference to a list of protocols this one conforms to
    protocols: uintptr_t = csd.csfield(Pointer64)
    #: a list of required instance methods (list reference)
    required_instance_methods: uintptr_t = csd.csfield(Pointer64)
    #: a list of required class methods (list reference)
    required_class_methods: uintptr_t = csd.csfield(Pointer64)
    #: a list of optional instance methods (list reference)
    optional_instance_methods: uintptr_t = csd.csfield(Pointer64)
    #: a list of optional class methods (list reference)
    optional_class_methods: uintptr_t = csd.csfield(Pointer64)
    #: all defined instance properties (list reference)
    instance_properties: uintptr_t = csd.csfield(Pointer64)
    #: the size of this struct
    size: uint32_t = csd.csfield(cs.Int32ul)  # sizeof(protocol_t)
    #: additional flags for this protocol
    flags: uint32_t = csd.csfield(cs.Int32ul)


@dc.dataclass
class TargetProtocolRaw32(TargetObjCObjectRaw32):
    name: uintptr_t = csd.csfield(Pointer32)
    protocols: uintptr_t = csd.csfield(Pointer32)
    required_instance_methods: uintptr_t = csd.csfield(Pointer32)
    required_class_methods: uintptr_t = csd.csfield(Pointer32)
    optional_instance_methods: uintptr_t = csd.csfield(Pointer32)
    optional_class_methods: uintptr_t = csd.csfield(Pointer32)
    instance_properties: uintptr_t = csd.csfield(Pointer32)
    size: uint32_t = csd.csfield(cs.Int32ul)  # sizeof(protocol_t)
    flags: uint32_t = csd.csfield(cs.Int32ul)


@dc.dataclass
class TargetProtocolList64(Virtual):
    #: According to Apple's source code:
    #:   - "count is pointer-sized by accident."
    count: uintptr_t = csd.csfield(Pointer64)


@dc.dataclass
class TargetProtocolList32(Virtual):
    count: uintptr_t = csd.csfield(Pointer32)


class TargetClassRO:  # NOTE: not a dataclass
    def is_swift(self) -> bool:
        return self.flags & 0x1

    def has_cxx_dtor(self) -> bool:
        return self.flags & (0x1 << 2)


@dc.dataclass
class TargetClassDataRaw64(TargetClassRO, Virtual):
    """Struct equivalent to ``class_data_ro_t``."""

    #: class flags (most common *is_swift* and *has_cxx_dtor*)
    flags: uint32_t = csd.csfield(cs.Int32ul)

    #: The instance starting point (unused)
    instance_start: uint32_t = csd.csfield(cs.Int32ul)

    #: The instance end point (unused)
    instance_end: uint32_t = csd.csfield(cs.Int32ul)

    #: Additional field on 64-bit systems (unused)
    reserved: uint32_t = csd.csfield(cs.Int32ul)

    #: A reference to the IVar layout - always zero (unused)
    ivar_layout: uintptr_t = csd.csfield(Pointer64)

    #: Pointer to the source-written name of this class
    name: uintptr_t = csd.csfield(Pointer64)

    #: A reference to all defined instance methods
    base_methods: uintptr_t = csd.csfield(Pointer64)

    #: A reference to all conformed protocols
    base_protocols: uintptr_t = csd.csfield(Pointer64)

    #: A pointer to a list of defined instance variables
    ivars: uintptr_t = csd.csfield(Pointer64)

    #: Reference to the weak instance variable layout (unused)
    weak_ivar_layout: uintptr_t = csd.csfield(Pointer64)

    #: A pointer to a list of all instance properties
    base_properties: uintptr_t = csd.csfield(Pointer64)


@dc.dataclass
class TargetClassDataRaw32(TargetClassRO, Virtual):
    flags: uint32_t = csd.csfield(cs.Int32ul)
    instance_start: uint32_t = csd.csfield(cs.Int32ul)
    instance_end: uint32_t = csd.csfield(cs.Int32ul)
    ivar_layout: uintptr_t = csd.csfield(Pointer32)
    name: uintptr_t = csd.csfield(Pointer32)
    base_methods: uintptr_t = csd.csfield(Pointer32)
    base_protocols: uintptr_t = csd.csfield(Pointer32)
    ivars: uintptr_t = csd.csfield(Pointer32)
    weak_ivar_layout: uintptr_t = csd.csfield(Pointer32)
    base_properties: uintptr_t = csd.csfield(Pointer32)


class ClassDataBits:
    def is_swift_stable(self) -> bool:
        return bool(self.bits & (1 << 1))

    def is_swift_legacy(self) -> bool:
        return bool(self.bits & (1 << 0))

    def is_swift(self) -> bool:
        """Returns whether the referenced class data points to a swift class.

        :return: whether the class is a swift class
        :rtype: bool
        """
        return self.is_swift_legacy() or self.is_swift_stable()


@dc.dataclass
class ClassDataBits32(ClassDataBits):
    bits: uint32_t = csd.csfield(cs.Int32ul)
    ptr: uintptr_t = csd.csfield(cs.Computed(lambda ctx: ctx.bits & 0xFFFFFFFC))


@dc.dataclass
class ClassDataBits64(ClassDataBits):
    """Additional data structure to measure the referenced class data location."""

    #: The actual bits of a reference
    bits: uint64_t = csd.csfield(cs.Int64ul)

    #: The 'decoded' pointer (computed at runtime)
    ptr: uintptr_t = csd.csfield(cs.Computed(lambda ctx: ctx.bits & 0x00007FFFFFFFFFF8))


@dc.dataclass
class TargetObjCClassRaw64(TargetObjCObjectRaw64):
    """The basic structure of Objective-C class interfaces."""

    #: The super class of this Objective-C class interface.
    superclass: uintptr_t = csd.csfield(Pointer64)

    #: Internal cache pointer (unused)
    cache: uintptr_t = csd.csfield(Pointer64)

    #: Reference to the internal VTable of this class interface (unused).
    vtable: uintptr_t = csd.csfield(Pointer64)

    #: A mangled reference to the actual class data.
    data: ClassDataBits64 = csd.csfield(ClassDataBits64)


@dc.dataclass
class TargetObjCClassRaw32(TargetObjCObjectRaw32):
    # metaclass: int = csd.csfield(Pointer32) === isa
    superclass: uintptr_t = csd.csfield(Pointer32)
    cache: uintptr_t = csd.csfield(Pointer32)
    vtable: uintptr_t = csd.csfield(Pointer32)
    data: ClassDataBits32 = csd.csfield(ClassDataBits32)


@dc.dataclass
class TargetSwiftClassRaw64(TargetObjCClassRaw64):
    flags: uint32_t = csd.csfield(cs.Int32ul)
    instance_address_offset: uint32_t = csd.csfield(cs.Int32ul)
    instance_size: uint32_t = csd.csfield(cs.Int32ul)
    instance_align_mask: uint16_t = csd.csfield(cs.Int16ul)
    reserved: uint16_t = csd.csfield(cs.Int16ul)
    class_size: uint32_t = csd.csfield(cs.Int32ul)
    class_address_offset: uint32_t = csd.csfield(cs.Int32ul)
    description: uintptr_t = csd.csfield(Pointer64)

    def base_address(self) -> int:
        return self._address - self.class_address_offset


@dc.dataclass
class TargetSwiftClassRaw32(TargetObjCClassRaw32):
    flags: uint32_t = csd.csfield(cs.Int32ul)
    instance_address_offset: uint32_t = csd.csfield(cs.Int32ul)
    instance_size: uint32_t = csd.csfield(cs.Int32ul)
    instance_align_mask: uint16_t = csd.csfield(cs.Int16ul)
    reserved: uint16_t = csd.csfield(cs.Int16ul)
    class_size: uint32_t = csd.csfield(cs.Int32ul)
    class_address_offset: uint32_t = csd.csfield(cs.Int32ul)
    description: uintptr_t = csd.csfield(Pointer32)

    def base_address(self) -> int:
        return self._address - self.class_address_offset


@dc.dataclass
class TargetCategoryRaw64(Virtual):
    """Raw struct of an Objective-C Category"""

    #: the catgory's name
    name: uintptr_t = csd.csfield(Pointer64)
    #: a reference to the base class of this category
    base_class: uintptr_t = csd.csfield(Pointer64)
    #: a reference to a list of instance methods
    instance_methods: uintptr_t = csd.csfield(Pointer64)
    #: a reference to all defined additional class methods
    class_methods: uintptr_t = csd.csfield(Pointer64)
    #: a reference to all additional conformed protocols
    base_protocols: uintptr_t = csd.csfield(Pointer64)
    #: pointer to a property list structure
    instance_properties: uintptr_t = csd.csfield(Pointer64)


@dc.dataclass
class TargetCategoryRaw32(Virtual):
    name: uintptr_t = csd.csfield(Pointer32)
    base_class: uintptr_t = csd.csfield(Pointer32)
    instance_methods: uintptr_t = csd.csfield(Pointer32)
    class_methods: uintptr_t = csd.csfield(Pointer32)
    base_protocols: uintptr_t = csd.csfield(Pointer32)
    instance_properties: uintptr_t = csd.csfield(Pointer32)


# There is no documentation on 32-bit CFStrings, so we won't
# include that structure
@dc.dataclass
class TargetCFStringRaw64(TargetObjCObjectRaw64):
    flags: uint64_t = csd.csfield(cs.Int64ul)
    value: uintptr_t = csd.csfield(Pointer64)
    characters: uint64_t = csd.csfield(cs.Int64ul)


# Typing extras
RawClassT = t.Union[TargetObjCClassRaw32, TargetObjCClassRaw64]
RawSwiftClassT = t.Union[TargetSwiftClassRaw64, TargetSwiftClassRaw32]
RawClassDataT = t.Union[TargetClassDataRaw32, TargetClassDataRaw64]
RawProtocolT = t.Union[TargetProtocolRaw32, TargetProtocolRaw64]
RawCategoryT = t.Union[TargetCategoryRaw32, TargetCategoryRaw64]
RawIVarT = t.Union[TargetIVarRaw32, TargetIVarRaw64]
RawPropertyT = t.Union[TargetPropertyRaw32, TargetPropertyRaw64]
RawMethodT = t.Union[TargetMethodRaw32, TargetMethodRaw64]
