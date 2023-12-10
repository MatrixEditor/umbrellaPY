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

from .demangler import (
    MangledName,
    demangle
)

from .relative_pointer import (
    # Type definitions first
    NotNull,
    Nullable,

    # Pointer types
    DirectPointer,
    RelativeDirectPointer,
    RelativeIndirectPointer,
    RelativeIndirectablePointer,
    CompactFunctionPointer,
    RelativeDirectPointerIntPair,
    RelativeIndirectablePointerIntPair,

    applyRelativeOffset,
    measureRelativeOffset
)

from .metadata_values import (
    # Context descriptor flags
    ContextDescriptorFlags,
    ContextDescriptorKind,
    TypeContextDescriptorFlags,
    AnonymousContextDescriptorFlags,

    # Enums and flags for generic contexts
    GenericPackKind,
    GenericParamKind,
    GenericRequirementFlags,
    GenericRequirementKind,

    # Protocol related enums and flags
    ProtocolClassConstraint,
    ProtocolContextDescriptorFlags,
    ProtocolRequirementKind,
    ProcolRequirementFlags,
    SpecialProtocol,
    ConformanceFlags,

    # field-related enums and flags
    FieldDescriptorKind,
    FieldRecordFlags,

    # Metadata
    MetadataInitializationKind,
    MetadataKind,
    TypeReferenceKind,

    # method-related flags and enums
    MethodDescriptorFlags,
    MethodDescriptorKind,

    # Other flags
    ClassFlags,
    ExtraClassDescriptorFlags
)

from .generic_context import (
    # basic structs
    GenericPackShapeHeader,
    GenericPackShapeDescriptor,
    GenericParamDescriptor,
    TargetGenericContext,
    TargetGenericContextDescriptorHeader,
    TargetGenericRequirementDescriptor,

    # partial specialization of trailing objects
    TrailingGenericContextObjects,
    RuntimeGenericSignature,
    TargetGenericSignature,
)

from .records import (
    # Fields
    FieldDescriptor,
    FieldRecord,

    # Associated types
    AssociatedTypeDescriptor,
    AssociatedTypeRecord,

    # Builtin types
    BuiltinTypeDescriptor,
)

from .metadata import (
    # Context descriptors
    TargetContextDescriptor,
    TargetTypeContextDescriptor,
    TargetModuleContextDescriptor,
    TargetAnonymousContextDescriptor,
    TargetOpaqueContextDescriptor,
    TargetExtensionContextDescriptor,
    TargetClassContextDescriptor,
    TargetProtocolContextDescriptor,
    TargetStructContextDescriptor,
    TargetEnumContextDescriptor,

    # protocol related
    TargetProtocolConformanceDescriptor,
    TargetProtocolRequirement,

    # Metadata structs
    TargetMetadata,
    TargetHeapMetadata,
    TargetTypeMetadataHeader,
    TargetTypeMetadataHeaderBase,
    TargetTypeMetadataLayoutPrefix,
    TargetClassMetadata,
    TargetAnyClassMetadata,

    # Metadata initialisation
    TargetForeignMetadataInitialization,
    TargetSingletonMetadataInitialization,

    # Class descriptor trailing objects
    TargetMethodOverrideDescriptor,
    TargetMethodDescriptor,
    TargetOverrideTableHeader,
    TargetVTableDescriptorHeader,
    TargetCanonicalSpecializedMetadataAccessorsListEntry,
    TargetCanonicalSpecializedMetadatasListCount,
    TargetCanonicalSpecializedMetadatasListEntry,
    TargetObjCResilientClassStubInfo,
    TargetResilientSuperclass,

    # Witnesses
    TargetWitnessTable,
    TargetResilientWitness,
    TargetResilientWitnessesHeader,
    TargetGenericWitnessTable,

    TargetMangledContextName,
    TargetTypeReference,
)

from .base import (
    ReflectionSectionKind,
    SwiftSectionIterator,
    DynamicSwiftSectionIterator,

    resolve_metadata_from_code
)

from .model import (
    ReflectionContext,
    has_swift_metadata
)

from .dumper import SwiftDumper