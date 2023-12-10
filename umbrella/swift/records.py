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

# APPLE SOURCE CODE LICENSE
# Copyright (c) 2014 - 2017 Apple Inc. and the Swift project authors
# Licensed under Apache License v2.0 with Runtime Library Exception
#
# See https://swift.org/LICENSE.txt for license information
# See https://swift.org/CONTRIBUTORS.txt for the list of Swift project authors

from __future__ import annotations

import dataclasses as dc
import typing as t

import construct as cs
import construct_dataclasses as csd

from umbrella.runtime import Virtual, VirtualArray, CString, sizeof
from umbrella.flags import Flags
from umbrella.swift import (
    RelativeDirectPointer,
    Nullable,
    MangledName,
    FieldDescriptorKind,
    FieldRecordFlags,
)


@dc.dataclass
class FieldRecord(Virtual):
    """
    Field records describe the type of a single stored property or case member
    of a class, struct or enum.
    """

    # Different flags that store information about the kind of this
    # field
    flags_value: int = csd.csfield(cs.Int32ul)
    flags: FieldRecordFlags = csd.csfield(Flags(FieldRecordFlags))

    mangled_typename: RelativeDirectPointer[MangledName, Nullable] = csd.csfield(
        RelativeDirectPointer(MangledName, True)
    )
    # NOTE: we can annotate the relative pointer with 'str' here, although we're
    # using CString as the struct reference.
    field_name: RelativeDirectPointer[str, Nullable] = csd.csfield(
        RelativeDirectPointer(CString, True)
    )

    def has_mangled_typename(self) -> bool:
        """Returns whether this field has a mangled type-name associated to it.

        :return: ture, if there is a mangled typename
        :rtype: bool
        """
        return not self.mangled_typename.is_null()

    def get_mangled_typename(self) -> bytes:
        return self.mangled_typename.get(self._address + 4)

    def get_field_name(self) -> t.Optional[str]:
        """Returns the field's name

        :return: the field's name
        :rtype: t.Optional[str]
        """
        return self.field_name.get(self._address + 8)

    def is_indirect_case(self) -> bool:
        """Returns whether this fields is an indirect case of an enum

        :return: true if this field is an indirect case
        :rtype: bool
        """
        return self.flags.is_indirect_case

    def is_var(self) -> bool:
        """Returns whether this field is a mutable `var` property.

        :return: true, if this field is mutable
        :rtype: bool
        """
        return self.flags.is_var

    def is_lazy(self) -> bool:
        return "$__lazy_storage_$" in self.get_field_name()


@dc.dataclass
class FieldDescriptor(Virtual):
    """
    Field descriptors contain a collection of field records for a single
    class, struct or enum declaration.
    """

    mangled_typename: RelativeDirectPointer[MangledName, Nullable] = csd.csfield(
        RelativeDirectPointer(MangledName, True)
    )
    super_class: RelativeDirectPointer[str, Nullable] = csd.csfield(
        RelativeDirectPointer(CString, True)
    )
    kind: FieldDescriptorKind = csd.tfield(
        FieldDescriptorKind, cs.Enum(cs.Int16ul, FieldDescriptorKind)
    )
    field_record_size: int = csd.csfield(cs.Int16ul)
    num_fields: int = csd.csfield(cs.Int32ul)

    def is_enum(self) -> bool:
        """Returns true if this field descriptor corresponds to an enum."""
        return self.kind in (
            FieldDescriptorKind.Enum,
            FieldDescriptorKind.MultiPayloadEnum,
        )

    def is_class(self) -> bool:
        """Returns true if this field descriptor corresponds to a class."""
        return self.kind in (FieldDescriptorKind.Class, FieldDescriptorKind.ObjCClass)

    def is_protocol(self) -> bool:
        """Returns true if this field descriptor corresponds to a protocol."""
        return self.kind in (
            FieldDescriptorKind.Protocol,
            FieldDescriptorKind.ClassProtocol,
            FieldDescriptorKind.ObjCProtocol,
        )

    def is_struct(self) -> bool:
        """Returns true if this field descriptor corresponds to a struct."""
        return self.kind == FieldDescriptorKind.Struct

    def has_mangled_typename(self) -> bool:
        """Returns whether this field descriptor has a mangled type-name associated to it.

        :return: ture, if there is a mangled typename
        :rtype: bool
        """
        return not self.mangled_typename.is_null()

    def has_super_class(self) -> bool:
        return not self.super_class.is_null()

    def get_fields(self) -> t.List[FieldRecord]:
        """Returns a list of all stores field records."""
        if self.num_fields == 0:
            return []

        # We have to use this, because FieldRecord extends Virtual
        address = self._address + sizeof(FieldDescriptor)
        struct = VirtualArray(self.num_fields, FieldRecord)
        return self._fp.read_struct(struct, address)

    def get_mangled_typename(self) -> t.Optional[bytes]:
        if not self.has_mangled_typename():
            return None
        return self.mangled_typename.get(self._address)

    def get_name_address(self) -> int:
        return self.mangled_typename.relative_offset + self._address

    def get_super_class(self) -> t.Optional[str]:
        if not self.has_super_class():
            return None

        address = self._address + 4
        return self.super_class.get(address)


# TODO: AssociatedTypeRecord
@dc.dataclass
class AssociatedTypeRecord(Virtual):
    """
    Associated type records describe the mapping from an associated
    type to the type witness of a conformance.
    """

    name: RelativeDirectPointer[str, Nullable] = csd.csfield(
        RelativeDirectPointer(CString, True)
    )
    substituted_typename: RelativeDirectPointer[str, Nullable] = csd.csfield(
        RelativeDirectPointer(CString, True)
    )

    def get_name(self) -> t.Optional[str]:
        """Returns the name of this record

        :return: the associated type name
        :rtype: t.Optional[str]
        """
        return self.name.get(self._address)

    def get_mangled_substituted_typename(self) -> t.Optional[str]:
        """Returns the mangled substituted type name

        :return: the mangled type name
        :rtype: t.Optional[str]
        """
        return self.substituted_typename.get(self._address + 4)


@dc.dataclass
class AssociatedTypeDescriptor(Virtual):
    """
    An associated type descriptor contains a collection of associated
    type records for a conformance.
    """

    conforming_typename: RelativeDirectPointer[str, Nullable] = csd.csfield(
        RelativeDirectPointer(CString, True)
    )
    protocol_typename: RelativeDirectPointer[str, Nullable] = csd.csfield(
        RelativeDirectPointer(CString, True)
    )

    num_associated_types: int = csd.csfield(cs.Int32ul)
    type_record_size: int = csd.csfield(cs.Int32ul)

    def get_mangled_protocol_type_name(self) -> t.Optional[str]:
        return self.protocol_typename.get(self._address + 4)

    def get_mangled_conforming_type_name(self) -> t.Optional[str]:
        return self.conforming_typename.get(self._address)

    def get_records(self) -> t.List[AssociatedTypeRecord]:
        """Returns a list of type records associated with this type.

        :return: a list of associated types
        :rtype: t.List[AssociatedTypeRecord]
        """
        if self.num_associated_types == 0:
            return []

        address = self._address + sizeof(AssociatedTypeDescriptor)
        struct = VirtualArray(self.num_associated_types, AssociatedTypeRecord)
        return self._fp.read_struct(struct, address)


@dc.dataclass
class BuiltinTypeDescriptor(Virtual):
    """
    Builtin type records describe basic layout information about
    any builtin types referenced from the other sections.
    """

    typename: RelativeDirectPointer[MangledName, Nullable] = csd.csfield(
        RelativeDirectPointer(MangledName, True)
    )
    size: int = csd.csfield(cs.Int32ul)

    # - Least significant 16 bits are the alignment.
    # - Bit 16 is 'bitwise takable'.
    # - Remaining bits are reserved.
    alignment_and_flags: int = csd.csfield(cs.Int32ul)
    stride: int = csd.csfield(cs.Int32ul)
    num_extra_inhabitants: int = csd.csfield(cs.Int32ul)

    def is_bitwise_takeable(self) -> bool:
        return bool((self.alignment_and_flags >> 16) & 1)

    def get_alignment(self) -> int:
        return self.alignment_and_flags & 0xFFFF

    def has_mangled_typename(self) -> bool:
        return not self.typename.is_null()

    def get_mangled_typename(self) -> t.Optional[bytes]:
        return self.typename.get(self._address)