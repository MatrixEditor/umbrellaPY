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

from typing import List, Iterable
from enum import IntEnum, Flag

import construct as cs


class FieldAccessFlags(Flag):
    ACC_PUBLIC = 0x0001
    ACC_PRIVATE = 0x0002
    ACC_PROTECTED = 0x0004
    ACC_STATIC = 0x0008
    ACC_FINAL = 0x0010
    ACC_VOLATILE = 0x0040
    ACC_TRANSIENT = 0x0080
    ACC_SYNTHETIC = 0x1000
    ACC_ENUM = 0x4000


class ClassAccessFlags(Flag):
    ACC_PUBLIC = 0x0001
    ACC_STATIC = 0x0008
    ACC_FINAL = 0x0010
    ACC_SUPER = 0x0020
    ACC_INTERFACE = 0x0200
    ACC_ABSTRACT = 0x0400
    ACC_SYNTHETIC = 0x1000
    ACC_ANNOTATION = 0x2000
    ACC_ENUM = 0x4000
    ACC_MODULE = 0x8000


class MethodAccessFlags(Flag):
    ACC_PUBLIC = 0x0001
    ACC_PRIVATE = 0x0002
    ACC_PROTECTED = 0x0004
    ACC_STATIC = 0x0008
    ACC_FINAL = 0x0010
    ACC_SYNCHRONIZED = 0x0020
    ACC_BRIDGE = 0x0040
    ACC_VARARGS = 0x0080
    ACC_NATIVE = 0x0100
    ACC_ABSTRACT = 0x0400
    ACC_STRICT = 0x0800
    ACC_SYNTHETIC = 0x1000


class ModuleAccessFlags(Flag):
    #: Indicates that this module is open.
    ACC_OPEN = 0x0020

    #: Indicates that this module was not explicitly or implicitly declared.
    ACC_SYNTHETIC = 0x1000

    #: Indicates that this module was implicitly declared.
    ACC_MANDATED = 0x8000


class ParameterAccessFlags(Flag):
    #: Indicates that the formal parameter was declared as `final`.
    ACC_FINAL = 0x0010

    #: Indicates that the formal parameter was not explicitly or implicitly
    #: declared in source code, as per the language specification in which the
    #: source code was written. (The formal parameter is an implementation
    #: artifact of the compiler that generated this class file.)
    ACC_SYNTHETIC = 0x1000

    #: Indicates that the formal parameter was implicitly declared in source
    #: code, following the specification of the language in which the source code
    #: was written. (The formal parameter is mandated by a language specification,
    #: and therefore, all compilers for the language must include it.)
    ACC_MANDATED = 0x8000


class ModuleRequiresAccessFlags(Flag):
    #: Indicates that any module dependent on the current module implicitly
    #: declares a dependency on the module specified by this entry.
    ACC_TRANSITIVE = 0x0020

    #: Indicates that this dependency is mandatory during the static phase
    #: (compile time) but optional during the dynamic phase (runtime).
    ACC_STATIC_PHASE = 0x0040

    #: Indicates that this dependency was not explicitly or implicitly declared
    #: in the source code of the module declaration.
    ACC_SYNTHETIC = 0x1000

    #: Indicates that this dependency was implicitly declared in the source code
    #: of the module declaration.
    ACC_MANDATED = 0x8000


class ModuleExportsAccessFlags(Flag):
    #: Indicates that this export was not explicitly or implicitly declared in
    #: the module declaration's source code.
    ACC_SYNTHETIC = 0x1000

    #: Indicates that this export was implicitly declared in the source code of
    #: the module declaration.
    ACC_MANDATED = 0x8000


class ModuleOpensAccessFlags(Flag):
    #: Indicates that this opening was not explicitly or implicitly declared in
    #: the source code of the module declaration.
    ACC_SYNTHETIC = 0x1000

    #: Indicates that this opening was implicitly declared in the source code of
    #: the module declaration.
    ACC_MANDATED = 0x8000


def list_flags(flags: int, model: Iterable[IntEnum]) -> List[str]:
    values = []
    for enum_value in model:
        if enum_value.value & flags != 0:
            values.append(enum_value.name.replace("ACC_", "").lower())
    return values


class AccessFlags:
    #: the raw flags value
    value: int
    #: all matched flags in a list (their names only)
    flags: List[str]
    #: the enum class
    model: type

    def __init__(self, value, model) -> None:
        self.value = value
        self.flags = list_flags(value, model)
        self.model = model

    def __repr__(self) -> str:
        return f"<AccessFlags {self.flags}>"


def Flags(model):
    return AccessFlagsAdapter(model)


class AccessFlagsAdapter(cs.Adapter):
    def __init__(self, model) -> None:
        super().__init__(cs.Int16ub)
        self.model = model

    def _decode(self, obj, context, path):
        return AccessFlags(obj, self.model)

    def _encode(self, obj: AccessFlags, context, path):
        return obj.value
