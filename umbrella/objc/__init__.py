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

# NOTE: mangling is not supported yet
from . import decoder

from .pointer import (
    Pointer32,
    Pointer64,
    PointerUnion,
    PointerUnion32,
    PointerUnion64
)

from .structs import (
    # Type definitions
    RawIVarT,
    RawCategoryT,
    RawClassDataT,
    RawClassT,
    RawMethodT,
    RawPropertyT,
    RawProtocolT,
    RawSwiftClassT,

    # 32-Bit arch structs
    TargetCategoryRaw32,
    TargetIVarRaw32,
    TargetMethodRaw32,
    TargetPropertyRaw32,
    TargetProtocolRaw32,
    TargetClassDataRaw32,
    TargetObjCClassRaw32,
    TargetProtocolList32,
    TargetObjCObjectRaw32,
    TargetSwiftClassRaw32,

    # 64-bit arch structs
    TargetIVarRaw64,
    TargetMethodRaw64,
    TargetCategoryRaw64,
    TargetPropertyRaw64,
    TargetProtocolRaw64,
    TargetClassDataRaw64,
    TargetObjCClassRaw64,
    TargetProtocolList64,
    TargetObjCObjectRaw64,
    TargetSwiftClassRaw64,

    # List structures
    TargetGenericList,
    TargetIVarList, # generic list
    TargetMethodList,
    TargetPropertyList, # generic list

    TargetCFStringRaw64,
    TargetSmallMethodRaw,
    ClassDataBits32,
    ClassDataBits64
)

from .base import (
    # internal iterator class -> maybe let this class be private
    BoundListIterator,

    # public runtime types
    ObjCCategory,
    ObjCClass,
    ObjCIVar,
    ObjCMethod,
    ObjCProperty,
    ObjCProtocol,
)

from .model import (
    # Basic cache to store all runtime selector strings
    SelectorCache,

    # These are global iterators that are not bound to any parent context
    ClassIterator,
    CategoryIterator,

    # Iterators that are bound to a parent type
    IVarIterator,
    MethodIterator,
    PropertyIterator,
    ProtocolIterator, # <optional bound>

    # The main runtime class
    ObjCMetadata,
    has_objc_metadata
)

# Use this class to create obj-c header files
from .dumper import ObjCDumper