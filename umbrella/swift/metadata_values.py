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

import enum

from typing import final
from umbrella.flags import FlagSet, from_flags

# The offset (in pointers) to the first requirement in a witness table.
WitnessTableFirstRequirementOffset = 1
MetadataKindIsNonHeap = 512


class ProtocolClassConstraint(enum.Enum):
    """Flag that indicates whether an existential type is class-constrained or not."""

    #: The protocol is class-constrained, so only class types can conform to it.
    #:
    #: This must be 0 for ABI compatibility with Objective-C protocol_t records.
    Class = False
    #: Any type can conform to the protocol.
    Any = True


class SpecialProtocol(enum.Enum):
    #: Not a special protocol.
    #:
    #: This must be 0 for ABI compatibility with Objective-C protocol_t records.
    NotSpecial = 0
    #: The Error protocol.
    Error = 1


@final
class ProtocolContextDescriptorFlags(FlagSet):
    """
    Flags for protocol context descriptors. These values are used as the
    kindSpecificFlags of the :class:`ContextDescriptorFlags` for the protocol.
    """

    def has_class_constraint(self) -> ProtocolClassConstraint:
        """Whether this protocol is class-constrained."""
        return from_flags(ProtocolClassConstraint, self.get_field(0, 1 * 8))

    def is_resilient(self) -> bool:
        """Whether this protocol is resilient."""
        return self.get_flag(1)

    def get_special_protocol_kind(self) -> SpecialProtocol:
        """Special protocol value."""
        return from_flags(SpecialProtocol, self.get_field(2, 6 * 8))


class MetadataKind(enum.IntEnum):
    """Kinds of Swift metadata records.  Some of these are types, some aren't. (not a complete view)"""

    Class = 0
    Struct = 0 | MetadataKindIsNonHeap
    Enum = 1 | MetadataKindIsNonHeap


@final
class ExtraClassDescriptorFlags(FlagSet):
    """
    Extra flags for resilient classes, since we need more than 16 bits of
    flags there.
    """

    def has_obj_c_resilient_class_stub(self) -> bool:
        return self.get_flag(0)


class TypeReferenceKind(enum.IntEnum):
    #: The conformance is for a nominal type referenced directly;
    #: getTypeDescriptor() points to the type context descriptor.
    DirectTypeDescriptor = 0x00

    #: The conformance is for a nominal type referenced indirectly;
    #: getTypeDescriptor() points to the type context descriptor.
    IndirectTypeDescriptor = 0x01

    #: The conformance is for an Objective-C class that should be looked up
    #: by class name.
    DirectObjCClassName = 0x02

    #: The conformance is for an Objective-C class that has no nominal type
    #: descriptor.
    #: getIndirectObjCClass() points to a variable that contains the pointer to
    #: the class object, which then requires a runtime call to get metadata.
    #:
    #: On platforms without Objective-C interoperability, this case is
    #: unused.
    IndirectObjCClass = 0x03


class MetadataInitializationKind(enum.IntEnum):
    #: There are either no special rules for initializing the metadata
    #: or the metadata is generic.  (Genericity is set in the
    #: non-kind-specific descriptor flags.)
    NoMetadataInitialization = 0

    #: The type requires non-trivial singleton initialization using the
    #: "in-place" code pattern.
    SingletonMetadataInitialization = 1

    #: The type requires non-trivial singleton initialization using the
    #: "foreign" code pattern.
    ForeignMetadataInitialization = 2


@final
class TypeContextDescriptorFlags(FlagSet):
    """
    Flags for nominal type context descriptors. These values are used as the
    kindSpecificFlags of the ContextDescriptorFlags for the type.
    """

    def __init__(self, __flags: int) -> None:
        self.flags = __flags
        #: Set if the context descriptor includes metadata for dynamically
        #: constructing a class's vtables at metadata instantiation time.
        #:
        #: Only meaningful for class descriptors
        self.has_vtable: bool = self.get_flag(15)

        #: Set if the context descriptor includes metadata for dynamically
        #: installing method overrides at metadata instantiation time.
        self.has_override_table: bool = self.get_flag(14)

        #: Set if the context descriptor is for a class with resilient ancestry.
        #:
        #: Only meaningful for class descriptors.
        self.has_resilient_super_class: bool = self.get_flag(13)

        #: Whether the immediate class members in this metadata are allocated
        #: at negative offsets.  For now, we don't use this.
        self.immediate_members_negativ: bool = self.get_flag(12)

        #: The kind of reference that this class makes to its resilient superclass
        #: descriptor.  A TypeReferenceKind.
        #:
        #: Only meaningful for class descriptors.
        self.resilient_superclass_reference_kind: TypeReferenceKind = from_flags(
            TypeReferenceKind, self.get_field(9, 3 * 8), 0x1F
        )

        #: Set if the type has extended import information.
        #:
        #: If true, a sequence of strings follow the null terminator in the
        #: descriptor, terminated by an empty string (i.e. by two null
        #: terminators in a row).  See TypeImportInfo for the details of
        #: these strings and the order in which they appear.
        #:
        #: Meaningful for all type-descriptor kinds.
        self.has_import_info: bool = self.get_flag(2)

        #: Set if the type descriptor has a pointer to a list of canonical
        #: prespecializations.
        self.has_canonical_metadata_prespecializations: bool = self.get_flag(3)

        #: Set if the metadata contains a pointer to a layout string
        self.has_layout_string: bool = self.get_flag(4)

        #: Set if the class is an actor.
        #:
        #: Only meaningful for class descriptors.
        self.is_actor: bool = self.get_flag(7)

        #: Set if the class is a default actor class.  Note that this is
        #: based on the best knowledge available to the class; actor
        #: classes with resilient superclassess might be default actors
        #: without knowing it.
        #:
        #: Only meaningful for class descriptors.
        self.is_default_actor: bool = self.get_flag(8)

        #: Whether there's something unusual about how the metadata is
        #: initialized.
        #:
        #: Meaningful for all type-descriptor kinds.
        self.meta_initialization: MetadataInitializationKind = from_flags(
            MetadataInitializationKind, self.get_field(0, 2), 0xFF
        )


class ClassFlags(enum.IntEnum):
    #: Is this a Swift class from the Darwin pre-stable ABI?
    #: This bit is clear in stable ABI Swift classes.
    #: The Objective-C runtime also reads this bit.
    IsSwiftPreStableABI = 0x1

    #: Does this class use Swift refcounting?
    UsesSwiftRefcounting = 0x2

    #: Has this class a custom name, specified with the @objc attribute?
    HasCustomObjCName = 0x4

    #: Whether this metadata is a specialization of a generic metadata pattern
    #: which was created during compilation.
    IsStaticSpecialization = 0x8

    #: Whether this metadata is a specialization of a generic metadata pattern
    #: which was created during compilation and made to be canonical by
    #: modifying the metadata accessor.
    IsCanonicalStaticSpecialization = 0x10


class ContextDescriptorKind(enum.IntEnum):  # uint8
    #: This context descriptor represents a module.
    Module = 0
    #: This context descriptor represents an extension.
    Extension = 1
    #: This context descriptor represents an anonymous possibly-generic context
    #: such as a function body.
    Anonymous = 2
    #: This context descriptor represents a protocol context.
    Protocol = 3
    #: This context descriptor represents an opaque type alias.
    Opaque = 4
    #: This context descriptor represents a class.
    Class = 16
    #: This context descriptor represents a struct.
    Struct = 17
    #: This context descriptor represents an enum.
    Enum = 18
    #: Last kind that represents a type of any sort.
    Type_Last = 31


class GenericRequirementKind(enum.IntEnum):
    #: A protocol requirement.
    Protocol = 0
    #: A same-type requirement.
    Sametype = 1
    #: A base class requirement.
    Baseclass = 2
    #: A "same-conformance" requirement, implied by a same-type or base-class
    #: constraint that binds a parameter with protocol requirements.
    SameConformance = 3
    #: A same-shape requirement between generic parameter packs.
    SameShape = 4
    #: A layout constraint.
    Layout = 0x1F


class ProtocolRequirementKind(enum.IntEnum):
    BaseProtocol = 0
    Method = enum.auto()
    Init = enum.auto()
    Getter = enum.auto()
    Setter = enum.auto()
    ReadCoroutine = enum.auto()
    ModifyCoroutine = enum.auto()
    AssociatedTypeAccessFunction = enum.auto()
    AssociatedConformanceAccessFunction = enum.auto()


@final
class ProcolRequirementFlags(FlagSet):
    """Flags that go in a ProtocolRequirement structure."""

    def __init__(self, __flags: int) -> None:
        super().__init__(__flags)
        #: The kind of the protocol requirement
        self.kind:  ProtocolRequirementKind = from_flags(ProtocolRequirementKind, __flags, mask=0x0F)
        #: whether the requirement is bound to an instance
        self.instance: bool = self.get_flag(4)


class MethodDescriptorKind(enum.IntEnum):
    Method = 0
    Init = enum.auto()
    Getter = enum.auto()
    Setter = enum.auto()
    ModifyCoroutine = enum.auto()
    ReadCoroutine = enum.auto()


class GenericParamKind(enum.IntEnum):
    #: A type parameter.
    Type = 0
    #: A type parameter pack.
    TypePack = 1
    Max = 0x3F


class GenericPackKind(enum.IntEnum):
    Metadata = 0
    WitnessTable = 1


class FieldDescriptorKind(enum.IntEnum):
    #: Swift nominal types.
    Struct = 0
    Class = enum.auto()
    Enum = enum.auto()

    #: Fixed-size multi-payload enums have a special descriptor format that
    #: encodes spare bits.
    MultiPayloadEnum = enum.auto()

    #: A Swift opaque protocol. There are no fields, just a record for the
    #: type itself.
    Protocol = enum.auto()

    #: A Swift class-bound protocol.
    ClassProtocol = enum.auto()

    #: An Objective-C protocol, which may be imported or defined in Swift.
    ObjCProtocol = enum.auto()

    #: An Objective-C class, which may be imported or defined in Swift.
    #: In the former case, field type metadata is not emitted, and
    #: must be obtained from the Objective-C runtime.
    ObjCClass = enum.auto()


@final
class FieldRecordFlags(FlagSet):
    def __init__(self, __flags: int) -> None:
        super().__init__(__flags)
        #: Is this a mutable `var` property?
        self.is_var: bool = self.get_flag(1)
        #: Is this an indirect enum case?
        self.is_indirect_case: bool = self.get_flag(0)
        #: Is this an artificial field?
        self.is_artificial: bool = self.get_flag(2)


@final
class AnonymousContextDescriptorFlags(FlagSet):
    def __init__(self, __flags: int) -> None:
        self.flags = __flags
        #: Whether this anonymous context descriptor is followed by its
        #: mangled name, which can be used to match the descriptor at runtime.
        self.has_mangled_name: bool = self.get_flag(0)


@final
class ConformanceFlags(FlagSet):
    def __init__(self, __flags: int) -> None:
        self.flags = __flags
        self.kind = (__flags & (0x7 << 3)) >> 3

        # Is the conformance "retroactive"?
        #
        # A conformance is retroactive when it occurs in a module that is
        # neither the module in which the protocol is defined nor the module
        # in which the conforming type is defined. With retroactive conformance,
        # it is possible to detect a conflict at run time.
        self.retroactive = self.get_flag(6)

        # Is the conformance synthesized in a non-unique manner?
        #
        # The Swift compiler will synthesize conformances on behalf of some
        # imported entities (e.g., C typedefs with the swift_wrapper attribute).
        # Such conformances are retroactive by nature, but the presence of multiple
        # such conformances is not a conflict because all synthesized conformances
        # will be equivalent.
        self.synthesized_not_unique = self.get_flag(7)

        # Retrieve the # of conditional requirements.
        self.num_conditional_requirements = self.get_field(8, 2 * 8)

        # Retrieve the # of conditional pack shape descriptors.
        self.num_conditional_pack_shape_descriptors = self.get_field(24, 2 * 8)

        # Whether this conformance has any resilient witnesses.
        self.has_resilient_witnesses = self.get_flag(16)

        # Whether this conformance has a generic witness table that may need to
        # be instantiated.
        self.has_generic_witness_table = self.get_flag(17)


@final
class MethodDescriptorFlags(FlagSet):
    """Flags that go in a MethodDescriptor structure."""

    def __init__(self, __flags: int) -> None:
        self.flags = __flags
        self.kind: MethodDescriptorKind = from_flags(MethodDescriptorKind, __flags, mask=0x0F)

        #: Is the method marked 'dynamic'?
        self.dynamic: bool = self.get_flag(5)

        #: Is the method an instance member?
        #: Note that 'init' is not considered an instance member.
        self.instance: bool = self.get_flag(4)

    def get_kind_name(self) -> str:
        if isinstance(self.kind, MethodDescriptorKind):
            return self.kind.name
        return f"<Unknown {self.kind}>"


@final
class ContextDescriptorFlags(FlagSet):
    def __init__(self, __flags: int) -> None:
        self.flags = __flags
        self.kind: ContextDescriptorKind = from_flags(ContextDescriptorKind, __flags, 0x1F)
        # Whether this is a unique record describing the referenced context.
        self.unique: bool = self.get_flag(6)
        # Whether the context being described is generic.
        self.generic: bool = self.get_flag(7)
        # The format version of the descriptor. Higher version numbers may have
        # additional fields that aren't present in older versions.
        self.version: int = self.get_field(8, (1 * 8))
        # The most significant two bytes of the flags word, which can have
        # kind-specific meaning.
        self.kind_flags: int = self.get_field(16, (2 * 8))


@final
class GenericRequirementFlags(FlagSet):
    #: the kind of this requirment
    kind: GenericRequirementKind
    #: whether this requirement is a key argument
    has_key_arg: bool

    def __init__(self, __flags: int) -> None:
        self.flags = __flags
        self.has_key_arg = self.get_flag(7)
        self.has_extra_arg = self.get_flag(6)
        self.kind = from_flags(GenericRequirementKind, __flags, 0x1F)
