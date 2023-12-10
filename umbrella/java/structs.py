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

# Descriptions taken from:
# ---------------------------------------------------------------------
# Specification: JSR-000924 Java Virtual Machine Specification
# Version: 7
# Status: Final Release
# Release: July 2011
#
# Copyright (c) 1997, 2013, Oracle America, Inc. and/or its affiliates.
# All rights reserved.
# 500 Oracle Parkway, Redwood City, California 94065, U.S.A.
# ---------------------------------------------------------------------

import typing as t
import dataclasses as dc

import construct as cs
import construct_dataclasses as csd


from umbrella.runtime import uint16_t, Virtual

from umbrella.java import ConstantPool, AccessFlags, Flags, ClassAccessFlags, attribute

kJavaClassFileMagic = b"\xCA\xFE\xBA\xBE"


@dc.dataclass
class ClassFile(Virtual):
    """Main structure to store all class-related data"""

    #: The magic item supplies the magic number identifying the class file
    #: format; it has the value 0xCAFEBABE.
    magic: bytes = csd.csfield(cs.Const(kJavaClassFileMagic))

    #: The values of the `minor_version` and `major_version` items represent the
    #: minor and major version numbers of this class file. These numbers together
    #: determine the class file format version.
    #: When a class file has a major version number of M and a minor version number
    #: of m, the format version of its class file is denoted as M.m. Consequently,
    #: class file format versions can be ordered lexicographically, for example, 1.5 <
    #: 2.0 < 2.1.
    minor_version: uint16_t = csd.csfield(cs.Int16ub)

    #: The major version, as described above.
    major_version: uint16_t = csd.csfield(cs.Int16ub)

    #: The constant pool for this class file.
    constant_pool: ConstantPool = csd.csfield(ConstantPool)

    #: The value of the access_flags item is a mask of flags used to denote
    #: access permissions to and properties of this class or interface
    access_flags: AccessFlags = csd.csfield(Flags(ClassAccessFlags))

    #: The value of the this_class item must be a valid index into the
    #: constant_pool table. The constant_pool entry at that index must be a
    #: CONSTANT_Class_info structure representing the class or interface
    #: defined by this class file.
    this_class: uint16_t = csd.csfield(cs.Int16ub)

    #: For a class, the value of the super_class item either must be zero or
    #: must be a valid index into the constant_pool table. If the value of
    #: the super_class item is nonzero, the constant_pool entry at that index
    #: must be a CONSTANT_Class_info structure representing the direct
    #: superclass of the class defined by this class file.
    super_class: uint16_t = csd.csfield(cs.Int16ub)

    #: The value of the interfaces_count item gives the number of direct
    #: superinterfaces of this class or interface type.
    num_interfaces: uint16_t = csd.csfield(cs.Int16ub)

    #: Each value in the interfaces array must be a valid index into the
    #: constant_pool table.
    interfaces: t.List[uint16_t] = csd.csfield(
        cs.Array(cs.this.num_interfaces, cs.Int16ub)
    )

    #: The value of the fields_count item gives the number of field_info structures
    #: in the fields table. The field_info structures represent all fields, both
    #: class variables and instance variables, declared by this class or interface
    #: type.
    num_fields: uint16_t = csd.csfield(cs.Int16ub)

    #: Each value in the fields table must be a field_info structure giving a
    #: complete description of a field in this class or interface
    fields: t.List[attribute.FieldInfo] = csd.subcsfield(
        attribute.FieldInfo,
        cs.Array(cs.this.num_fields, csd.to_struct(attribute.FieldInfo)),
    )

    #: The value of the methods_count item gives the number of method_info structures
    #: in the methods table.
    num_methods: uint16_t = csd.csfield(cs.Int16ub)

    #: Each value in the methods table must be a method_info structure giving a
    #: complete description of a method in this class or interface.
    methods: t.List[attribute.MethodInfo] = csd.subcsfield(
        attribute.MethodInfo,
        cs.Array(cs.this.num_methods, csd.to_struct(attribute.MethodInfo)),
    )

    #: The value of the attributes_count item gives the number of attributes in
    #: the attributes table of this class.
    num_attributes: uint16_t = csd.csfield(cs.Int16ub)

    #: Each value of the attributes table must be an :class:`AttributeInfo` structure.
    attributes: t.List[attribute.AttributeInfo] = csd.subcsfield(
        attribute.AttributeInfo,
        cs.Array(cs.this.num_attributes, csd.to_struct(attribute.AttributeInfo)),
    )

    def get_name(self) -> str:
        # 'this_class' stores an index to the actual class name
        index = self.get_constant(self.this_class).value
        return self.get_constant(index).value

    def get_super_class_name(self) -> t.Optional[str]:
        if self.super_class:
            index = self.get_constant(self.super_class).value
            return self.get_constant(index).value

    def get_constant(self, index: int):
        return self.constant_pool[index].data

    def get_interface_names(self) -> t.List[str]:
        return list(map(lambda x: self.get_constant(x).value, self.interfaces))

    def __str__(self) -> str:
        return f"<JavaClassFile '{self.get_name()}'>"
