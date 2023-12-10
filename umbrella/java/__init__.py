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

from .access_flags import (
    ClassAccessFlags,
    ModuleAccessFlags,
    FieldAccessFlags,
    MethodAccessFlags,
    ParameterAccessFlags,
    ModuleRequiresAccessFlags,
    ModuleExportsAccessFlags,
    ModuleOpensAccessFlags,

    AccessFlags,
    Flags,

    list_flags
)

from .constant_pool import (
    ConstantPool,
    ConstantInfo,
    ConstantInfoKind,

    # Constant Types
    ConstantClass,
    ConstantDouble,
    ConstantDynamic,
    ConstantFieldRef,
    ConstantFloat,
    ConstantInteger,
    ConstantInterfaceMethodRef,
    ConstantInvokeDynamic,
    ConstantLong,
    ConstantMethodHandle,
    ConstantMethodRef,
    ConstantMethodType,
    ConstantModule,
    ConstantNameAndType,
    ConstantNameAndTypeRef,
    ConstantPackage,
    ConstantString,
    ConstantUTF8
)

# "attributes" stores classes that may load to name confusions, so we only
# import the module here
from . import attribute

from .structs import (
    kJavaClassFileMagic,
    ClassFile
)

from .file import JavaClassFile