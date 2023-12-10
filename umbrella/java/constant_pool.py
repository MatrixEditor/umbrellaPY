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

# Field descriptions taken from:
# ---------------------------------------------------------------------
# Specification: JSR-396 Java SE 21
# Version: 21
# Status: Final Release
# Release: September 2023
#
# Copyright © 1997, 2023, Oracle America, Inc.
# All rights reserved.
# ---------------------------------------------------------------------

import typing as t
import enum
import dataclasses as dc

import construct as cs
import construct_dataclasses as csd


from umbrella.runtime import uint16_t, uint32_t, uint64_t, uint8_t
from umbrella.flags import Flags


class ConstantInfoKind(enum.IntEnum):
    UTF8 = 1
    INTEGER = 3
    FLOAT = 4
    LONG = 5
    DOUBLE = 6
    CLASS = 7
    STRING = 8
    FIELD_REF = 9
    METHOD_REF = 10
    INTERFACE_METHOD_REF = 11
    NAME_AND_TYPE = 12
    METHOD_HANDLE = 15
    METHOD_TYPE = 16
    DYNAMIC = 17
    INVOKE_DYNAMIC = 18
    MODULE = 19
    PACKAGE = 20


@csd.dataclass_struct
class ConstantUTF8:
    length: uint16_t = csd.csfield(cs.Int16ub)
    value: str = csd.csfield(cs.StringEncoded(cs.Bytes(cs.this.length), "utf-8"))


@csd.dataclass_struct
class ConstantInteger:
    #: The bytes of the value are stored in big-endian (high byte first) order.
    value: uint32_t = csd.csfield(cs.Int32ub)


@csd.dataclass_struct
class ConstantFloat:
    #: The bytes of the single format representation are stored in big-endian
    #: (high byte first) order.
    value: float = csd.csfield(cs.Float32b)


@csd.dataclass_struct
class ConstantDouble:
    value: float = csd.csfield(cs.Float64b)


@csd.dataclass_struct
class ConstantLong:
    value: uint64_t = csd.csfield(cs.Int64ub)


@csd.dataclass_struct
class ConstantRef:
    #: The value of the name_index item must be a valid index into the
    #: constant_pool table. The constant_pool entry at that index must be a
    #: CONSTANT_Utf8_info structure representing a valid string encoded in
    #: internal form.
    value: uint16_t = csd.csfield(cs.Int16ub)


ConstantClass = ConstantRef
ConstantString = ConstantRef
ConstantMethodType = ConstantRef
ConstantModule = ConstantRef
ConstantPackage = ConstantRef


@csd.dataclass_struct
class ConstantNameAndType:
    #: The `name_index` item's value must be a valid index within the
    #: `constant_pool` table. The entry in the `constant_pool` at that index must be a
    #: `ConstantUTF8` structure, representing either the special method name `<init>`
    #: or a valid unqualified name (§4.2.2) that identifies a field or method.
    name_index: uint16_t = csd.csfield(cs.Int16ub)

    #: The type_index item's value must be a valid index within the
    #: `constant_pool` table. The entry in the `constant_pool` at that index must be a
    #: `ConstantUTF8` structure, representing a valid field descriptor or method
    #: descriptor.
    type_index: uint16_t = csd.csfield(cs.Int16ub)


@csd.dataclass_struct
class ConstantNameAndTypeRef:
    #: The `class_index` item's value must be a valid index within the
    #: `constant_pool` table. The entry in the `constant_pool` at that index
    #: must be a `ConstantClass` structure representing a class or interface
    #: type that includes the field or method as a member.
    class_index: uint16_t = csd.csfield(cs.Int16ub)

    #: The `name_and_type_index` item's value must be a valid index within
    #: the `constant_pool` table. The entry in the `constant_pool` at that index
    #: must be a `ConstantNameAndType` structure. This entry in the
    #: `constant_pool` specifies the name and descriptor of the field or method.
    name_and_type_index: uint16_t = csd.csfield(cs.Int16ub)


ConstantFieldRef = ConstantNameAndTypeRef
ConstantMethodRef = ConstantNameAndTypeRef
ConstantInterfaceMethodRef = ConstantNameAndTypeRef


@csd.dataclass_struct
class ConstantMethodHandle:
    #: The `reference_kind` item's value must be within the range of 1 to 9. This value
    #: signifies the type of this method handle, describing its bytecode behavior.
    reference_kind: uint8_t = csd.csfield(cs.Int8ub)

    #: The value of the reference_index item must be a valid index into the constant_pool table.
    reference_index: uint16_t = csd.csfield(cs.Int16ub)


@csd.dataclass_struct
class ConstantInvokeDynamic:
    #: The `bootstrap_method_attr_index` item's value must be a valid index within the
    #: `bootstrap_methods` array of the bootstrap method table in this class file.
    bootstrap_method_attr_index: uint16_t = csd.csfield(cs.Int16ub)

    #: The `name_and_type_index` item's value must be a valid index within the `constant_pool`
    #: table. The entry in the `constant_pool` at that index must be a `ConstantNameAndType` structure
    #: representing a method name and method descriptor.
    reference_index: uint16_t = csd.csfield(cs.Int16ub)

ConstantDynamic = ConstantInvokeDynamic

@csd.dataclass_struct
class ConstantInfo:
    #: Each item in the constant_pool table must begin with a 1-byte tag indicating
    #: the kind of the entry.
    tag_value: uint8_t = csd.csfield(cs.Int8ub)
    #: the parsed kind
    tag: ConstantInfoKind = csd.csfield(Flags(ConstantInfoKind, "tag_value"))
    #: based on the specified tag one of the structures defined above
    data: t.Any = csd.csfield(
        cs.Switch(
            cs.this.tag,
            cases={
                ConstantInfoKind.UTF8: ConstantUTF8.parser,
                ConstantInfoKind.INTEGER: ConstantInteger.parser,
                ConstantInfoKind.FLOAT: ConstantFloat.parser,
                ConstantInfoKind.LONG: ConstantLong.parser,
                ConstantInfoKind.DOUBLE: ConstantDouble.parser,
                ConstantInfoKind.CLASS: ConstantClass.parser,
                ConstantInfoKind.STRING: ConstantString.parser,
                ConstantInfoKind.FIELD_REF: ConstantFieldRef.parser,
                ConstantInfoKind.METHOD_REF: ConstantMethodRef.parser,
                ConstantInfoKind.INTERFACE_METHOD_REF: ConstantInterfaceMethodRef.parser,
                ConstantInfoKind.NAME_AND_TYPE: ConstantNameAndType.parser,
                ConstantInfoKind.METHOD_HANDLE: ConstantMethodHandle.parser,
                ConstantInfoKind.METHOD_TYPE: ConstantMethodType.parser,
                ConstantInfoKind.INVOKE_DYNAMIC: ConstantInvokeDynamic.parser,
                ConstantInfoKind.DYNAMIC: ConstantDynamic.parser,
            },
        )
    )


@dc.dataclass
class ConstantPool:
    #: The value of the constant_pool_count item is equal to the number of
    #: entries in the constant_pool table plus one. A constant_pool index
    #: is considered valid if it is greater than zero and less than 'count'.
    count: uint16_t = csd.csfield(cs.Int16ub)

    #: The constant_pool is a table of structures representing various string
    #: constants, class and interface names, field names, and other constants
    #: that are referred to within the ClassFile structure and its substructures.
    #: The format of each constant_pool table entry is indicated by its first
    #: "tag" byte.
    pool: t.List[ConstantInfo] = csd.csfield(
        cs.Array(cs.this.count - 1, ConstantInfo.parser)
    )

    def index(self, kind: ConstantInfoKind) -> int:
        for i, entry in enumerate(self.pool):
            if entry.tag == kind:
                # add one here as we start counting from 1
                return i + 1
        return -1

    def __getitem__(self, index: int) -> t.Optional[ConstantInfo]:
        # TODO: explain why
        if index > 0:
            return self.pool[index - 1]
