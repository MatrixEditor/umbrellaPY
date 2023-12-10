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

# -----------------------------------------------------------------------------
# IMPORTANT NOTES:
# It is recommended to use STRG+F to search for the preferred structure as this
# source file is just too long. Otherwise, it is also possible to use the
# documentation available on Github-Pages.
# -----------------------------------------------------------------------------

import dataclasses as dc
import typing as t

import construct as cs
import construct_dataclasses as csd

from umbrella.flags import Flags
from umbrella.runtime import AlignedUnion, CString, Virtual, Void, sizeof
from umbrella.swift import (
    AnonymousContextDescriptorFlags,
    CompactFunctionPointer,
    ContextDescriptorFlags,
    ContextDescriptorKind,
    DirectPointer,
    FieldDescriptor,
    MetadataInitializationKind,
    MetadataKind,
    MethodDescriptorFlags,
    NotNull,
    Nullable,
    ProcolRequirementFlags,
    ProtocolContextDescriptorFlags,
    RelativeDirectPointer,
    RelativeIndirectablePointer,
    RelativeIndirectPointer,
    TargetGenericContext,
    TargetGenericContextDescriptorHeader,
    TargetGenericRequirementDescriptor,
    TargetGenericSignature,
    TrailingGenericContextObjects,
    TypeContextDescriptorFlags,
    TypeReferenceKind,
    GenericPackShapeDescriptor,
    ConformanceFlags,
    ClassFlags,
    applyRelativeOffset,
)
from umbrella.trailing_objects import Token, TrailingObjects


#: The name of the fake module used to hold imported Objective-C things.
MANGLING_MODULE_OBJC = "__C"


def is_c_imported_name(name: str) -> bool:
    # This does not include MANGLING_MODULE_CLANG_IMPORTER because that's
    # used only for synthesized declarations and not actual imported
    # declarations.
    return name == MANGLING_MODULE_OBJC


#: This type var is a trick to be able to cast context descriptors to their
#: actual type.
T = t.TypeVar("T", bound="TargetContextDescriptor")


@dc.dataclass
class TargetContextDescriptor(Virtual):
    """Base class for all context descriptors.

    This type is also references as a _NominalTypeDescriptor_. Actually, the Swift
    ABI names this struct _TargetContextDescriptor_, and so do we. Note that this
    type only stores the following fields:

    - ``flags``: general context descriptor flags (including its kind)
    - ``parent``: the parent descriptor (null if this is a module descriptor)
    """

    #: Common flags stored in the first 32-bit word of any context descriptor.
    flags_value: int = csd.csfield(cs.Int32ul)
    #: Flags describing the context, including its kind and format version.
    flags: ContextDescriptorFlags = csd.csfield(Flags(ContextDescriptorFlags))

    # IMPORTANT: This method is used to determine the parent type dynamically at
    # runtime.
    @staticmethod
    def get_type(kind: ContextDescriptorKind) -> t.Type[TargetContextDescriptor]:
        cls = TargetContextDescriptor
        name = f"Target{kind.name}ContextDescriptor"
        # REVISIT: maybe put this import to the top of this file
        from umbrella import swift
        return getattr(swift, name, cls)

    def cast(self, ty: t.Type[T] = None) -> t.Union[T, t.Self]:
        """
        Casts this context descriptor to the right type (if not
        already done)
        """

        # Before parsing the struct again, we can check if the
        # target type is ours
        kind = self.get_kind()
        ty = ty or TargetContextDescriptor.get_type(kind)
        if ty == type(self):
            return self

        assert hasattr(self, "_fp"), "Casting not supported"
        # Otherwise try to parse the data again
        ty = ty or TargetContextDescriptor.get_type(self.get_kind())
        return self._fp.read_struct(ty, self._address)

    #: The parent context, or null if this is a top-level context.
    parent: RelativeIndirectablePointer[
        TargetContextDescriptor, Nullable
    ] = csd.csfield(RelativeIndirectablePointer(lambda: TargetContextDescriptor, True))

    def get_parent(self) -> t.Optional[TargetContextDescriptor]:
        return self.parent.get(self._address + 4)

    # Some helper functions around basic context information
    def is_generic(self) -> bool:
        return self.flags.generic

    def is_unique(self) -> bool:
        return self.flags.unique

    def get_kind(self) -> ContextDescriptorKind:
        return self.flags.kind

    def get_generic_context(self) -> TargetGenericContext:
        """
        Get the generic context information for this context, or null if the
        context is not generic.
        """
        raise NotImplementedError("Must be implemented in a sub-class!")

    def get_module_context(self) -> TargetModuleContextDescriptor:
        """Get the module context for this context."""
        if self.get_kind() == ContextDescriptorKind.Module:
            return self

        parent = self.parent.get(self._address + 4, fp=self._fp)
        if not parent:
            raise TypeError("Could not find module at " + str(self._address))

        if parent.get_kind() == ContextDescriptorKind.Module:
            return parent.cast()
        # All context chains should eventually find a module.
        return parent.get_module_context()

    def is_c_imported_context(self) -> bool:
        """Is this context part of a C-imported module?"""

        # This method gets overriden in the actual module context
        return self.get_module_context().is_c_imported_context()

    def get_num_generic_params(self) -> int:
        generic_context = self.get_generic_context()
        if generic_context is None:
            return 0

        return generic_context.get_generic_context_header().num_params

    def get_mangled_name(self) -> t.Optional[str]:
        raise NotImplementedError("Must be implemented in sub-class!")

    def __hash__(self) -> int:
        #: TODO: inspect why we have to define this method again
        return self._address


@dc.dataclass
class TargetRelativeContextPointer:
    """A relative pointer to a type context descriptor."""

    #: We have to pack this pointer into a dataclass, because it is used
    #: as a trailing object within a ProtocolDescriptor
    ptr: RelativeIndirectablePointer[TargetContextDescriptor, Nullable] = csd.csfield(
        RelativeIndirectablePointer(TargetContextDescriptor, True)
    )


@dc.dataclass
class TargetModuleContextDescriptor(TargetContextDescriptor):
    """Descriptor for a module context."""

    #: The module name.
    name: RelativeDirectPointer[str, NotNull] = csd.csfield(
        # Note the use of 'CString' here. The default 'Runtime' class implements
        # an internal check before parsing the struct to be able to parse
        # strings.
        RelativeDirectPointer(CString)
    )

    def is_c_imported_context(self) -> bool:
        """Is this module a special C-imported module?"""
        return is_c_imported_name(self.get_mangled_name())

    def get_mangled_name(self) -> str:
        address = self._address + sizeof(TargetContextDescriptor)
        return self.name.get(address, self._fp)


@dc.dataclass
class TargetExtensionContextDescriptor(
    TargetContextDescriptor,
    TrailingGenericContextObjects[
        TargetGenericContextDescriptorHeader, *TargetGenericSignature
    ],
):
    """Descriptor for an extension context."""

    #: A mangling of the `Self` type context that the extension extends.
    #: The mangled name represents the type in the generic context encoded by
    #: this descriptor. For example, a nongeneric nominal type extension will
    #: encode the nominal type name. A generic nominal type extension will encode
    #: the instance of the type with any generic arguments bound.
    #
    #: Note that the Parent of the extension will be the module context the
    #: extension is declared inside.
    extended_context: RelativeDirectPointer[str, Nullable] = csd.csfield(
        RelativeDirectPointer(CString)
    )

    def get_mangled_extended_context(self) -> t.Optional[str]:
        offset = self._address + sizeof(TargetContextDescriptor)
        return self.extended_context.get(offset)

    def get_mangled_name(self) -> t.Optional[str]:
        return self.get_mangled_extended_context()


@dc.dataclass
class TargetMangledContextName:
    #: The mangled name of the context.
    name: RelativeDirectPointer[str, NotNull] = csd.csfield(
        RelativeDirectPointer(CString)
    )


@dc.dataclass
class TargetAnonymousContextDescriptor(
    TargetContextDescriptor,
    TrailingGenericContextObjects[
        TargetGenericContextDescriptorHeader,
        *TargetGenericSignature,
        TargetMangledContextName,
    ],
):
    """Descriptor for an anonymous context."""

    def get_kind_flags(self) -> AnonymousContextDescriptorFlags:
        return AnonymousContextDescriptorFlags(self.flags.kind_flags)

    def has_mangled_name(self) -> bool:
        """
        Whether this anonymous context descriptor contains a full mangled name,
        which can be used to match the anonymous type to its textual form.
        """
        return self.get_kind_flags().has_mangled_name

    def get_mangled_name(self) -> t.Optional[str]:
        """
        Retrieve the mangled name of this context, or NULL if it was not
        recorded in the metadata.
        """
        if not self.has_mangled_name():
            return None

        name = self.get_mangled_context_name().name
        index = self._index_of(Token[TargetMangledContextName])
        address = self._get_address(index)
        return name.get(address)

    def get_mangled_context_name(self) -> t.Optional[TargetMangledContextName]:
        """Retrieve a pointer to the mangled context name structure."""
        if not self.has_mangled_name():
            return None

        return self.getTrailingObject(Token[TargetMangledContextName])

    def _num_target_mangled_context_name(self) -> int:
        return int(self.has_mangled_name())


@dc.dataclass
class TargetProtocolRequirement(Virtual):
    """A protocol requirement descriptor.

    This describes a single protocol requirement in a protocol descriptor. The
    index of the requirement in the descriptor determines the offset of the
    witness in a witness table for this protocol.
    """

    flags_value: int = csd.csfield(cs.Int32ul)
    flags: ProcolRequirementFlags = csd.csfield(Flags(ProcolRequirementFlags))

    #: The optional default implementation of the protocol.
    implementation: RelativeDirectPointer[Void, Nullable] = csd.csfield(
        RelativeDirectPointer(Void, True)
    )


@dc.dataclass
class TargetProtocolContextDescriptor(
    TargetContextDescriptor,
    TrailingObjects[
        TargetGenericRequirementDescriptor,
        TargetProtocolRequirement,
    ],
):
    """A protocol descriptor.

    Protocol descriptors contain information about the contents of a protocol:
    it's name, requirements, requirement signature, context, and so on. They
    are used both to identify a protocol and to reason about its contents.

    Only Swift protocols are defined by a protocol descriptor, whereas
    Objective-C (including protocols defined in Swift as @objc) use the
    Objective-C protocol layout.
    """

    #: The name of the protocol.
    name: RelativeDirectPointer[str, NotNull] = csd.csfield(
        RelativeDirectPointer(CString)
    )

    #: The number of generic requirements in the requirement signature of the
    #: protocol.
    num_requirements_in_signature: int = csd.csfield(cs.Int32ul)

    #: The number of requirements in the protocol.
    #: If any requirements beyond MinimumWitnessTableSizeInWords are present
    #: in the witness table template, they will be not be overwritten with
    #: defaults.
    num_requirements: int = csd.csfield(cs.Int32ul)

    def _num_target_generic_requirement_descriptor(self) -> int:
        return self.num_requirements_in_signature

    def _num_target_protocol_requirement(self) -> int:
        return self.num_requirements

    #: Associated type names, as a space-separated list in the same order
    #: as the requirements.
    associated_type_names: RelativeDirectPointer[str, Nullable] = csd.csfield(
        RelativeDirectPointer(CString, True)
    )

    def get_associated_type_names(self) -> t.List[str]:
        if self.associated_type_names.is_null():
            return []
        address = self._address + sizeof(TargetContextDescriptor) + 12
        return self.associated_type_names.get(address).split(" ")

    def get_protocol_context_descriptor_flags(self) -> ProtocolContextDescriptorFlags:
        return ProtocolContextDescriptorFlags(self.flags.kind_flags)

    def get_requirements_in_signature(
        self,
    ) -> t.List[TargetGenericRequirementDescriptor]:
        """
        Retrieve the requirements that make up the requirement signature of
        this protocol.
        """

        # Use this check rather than relying on getTrailingObjects
        if self.num_requirements_in_signature == 0:
            return []

        return list(self.getTrailingObjects(Token[TargetGenericRequirementDescriptor]))

    def get_requirements(self) -> t.List[TargetProtocolRequirement]:
        if self.num_requirements == 0:
            return []

        return list(self.getTrailingObjects(Token[TargetProtocolRequirement]))

    def get_name_offset(self) -> int:
        return self._address + sizeof(TargetContextDescriptor)

    def get_mangled_name(self) -> str:
        return self.name.get(self.get_name_offset())

    def get_requirements_base_descriptor(self) -> t.Optional[int]:
        """Retrieve the requirement base descriptor address."""
        if self.num_requirements == 0:
            return None

        pos = self._index_of(Token[TargetProtocolRequirement])
        assert pos != -1, "Negative index!"
        return self._get_address(pos)


@dc.dataclass
class TargetOpaqueContextDescriptor(
    TargetContextDescriptor,
    TrailingGenericContextObjects[
        TargetGenericContextDescriptorHeader,
        *TargetGenericSignature,
        RelativeDirectPointer(CString, nullable=True),
    ],
):
    """The descriptor for an opaque type. (like typing.Any)"""

    def get_num_underlying_type_args(self) -> int:
        """
        The kind-specific flags area is used to store the count of the generic
        arguments for underlying type(s) encoded in the descriptor.
        """
        return self.flags.kind_flags

    def _num_relative_direct_pointer(self) -> int:
        return self.get_num_underlying_type_args()

    def get_underlying_type_argument(
        self, index: int
    ) -> t.Optional[RelativeDirectPointer[str, Nullable]]:
        if self.get_num_underlying_type_args() <= index:
            return None
        # As TrailingObjects caches each values after the
        # first time it has been parsed, we can call
        # getTrailingObjects as much as we want.
        values = list(self.getTrailingObjects(Token[RelativeDirectPointer]))
        return values[index]


@dc.dataclass
class TargetSingletonMetadataInitialization(Virtual):
    #: The initialization cache.  Out-of-line because mutable.
    cache: RelativeDirectPointer[Void, Nullable] = csd.csfield(
        RelativeDirectPointer(Void, True)
    )

    #: union: (TODO: implement me)
    #: The incomplete metadata, for structs, enums and classes without
    #: resilient ancestry.
    #: --- OR ---
    #: If the class descriptor's hasResilientSuperclass() flag is set,
    #: this field instead points at a pattern used to allocate and
    #: initialize metadata for this class, since it's size and contents
    #: is not known at compile time.
    pattern: RelativeDirectPointer[Void, Nullable] = csd.csfield(
        RelativeDirectPointer(Void, True)
    )

    #: The completion function.  The pattern will always be null, even
    #: for a resilient class.
    completion_func: RelativeDirectPointer[Void, Nullable] = csd.csfield(
        RelativeDirectPointer(Void, True)
    )


@dc.dataclass  #: TargetForeignMetadataInitialization<Runtime>
class TargetForeignMetadataInitialization(Virtual):
    """
    The control structure for performing non-trivial initialization of
    singleton foreign metadata.
    """

    #: The completion function.  The pattern will always be null.
    cache: RelativeDirectPointer[Void, Nullable] = csd.csfield(
        RelativeDirectPointer(Void, True)
    )


@dc.dataclass
class TargetTypeGenericContextDescriptorHeader(Virtual):
    #: The metadata instantiation cache.
    instantiation_cache: RelativeDirectPointer[Void, Nullable] = csd.csfield(
        RelativeDirectPointer(Void, True)
    )

    #: The default instantiation pattern.
    instantiation_pattern: RelativeDirectPointer[Void, Nullable] = csd.csfield(
        RelativeDirectPointer(Void, True)
    )

    #: The base header.  Must always be the final member.
    base: TargetGenericContextDescriptorHeader = csd.csfield(
        TargetGenericContextDescriptorHeader
    )


@dc.dataclass
class TargetResilientSuperclass(Virtual):
    #: The superclass of this class.  This pointer can be interpreted
    #: using the superclass reference kind stored in the type context
    #: descriptor flags.  It is null if the class has no formal superclass.
    #:
    #: Note that SwiftObject, the implicit superclass of all Swift root
    #: classes when building with ObjC compatibility, does not appear here.
    super_class: RelativeDirectPointer[str, Nullable] = csd.csfield(
        RelativeDirectPointer(CString, True)
    )


@dc.dataclass
class TargetObjCResilientClassStubInfo(Virtual):
    """A structure that stores a reference to an Objective-C class stub.

    This is not the class stub itself; it is part of a class context
    descriptor.
    """

    #: A relative pointer to an Objective-C resilient class stub.
    #:
    #: We do not declare a struct type for class stubs since the Swift runtime
    #: does not need to interpret them. The class stub struct is part of
    #: the Objective-C ABI, and is laid out as follows:
    #: - isa pointer, always 1
    #: - an update callback, of type 'Class (*)(Class *, objc_class_stub *)'
    #:
    #: Class stubs are used for two purposes:
    #:
    #: - Objective-C can reference class stubs when calling static methods.
    #: - Objective-C and Swift can reference class stubs when emitting
    #:   categories (in Swift, extensions with @objc members).
    super_class: RelativeDirectPointer[Void, Nullable] = csd.csfield(
        RelativeDirectPointer(Void, True)
    )


@dc.dataclass
class TargetVTableDescriptorHeader(Virtual):
    """Header for a class vtable descriptor.

    This is a variable-sized structure that describes how to find and parse a
    vtable within the type metadata for a class.
    """

    #: The offset of the vtable for this class in its metadata, if any,
    #: in words.
    #:
    #: If this class has a resilient superclass, this offset is relative to the
    #: the start of the immediate class's metadata. Otherwise, it is relative
    #: to the metadata address point.
    vtable_offset: int = csd.csfield(cs.Int32ul)

    #: The number of vtable entries. This is the number of MethodDescriptor
    #: records following the vtable header in the class's nominal type
    #: descriptor, which is equal to the number of words this subclass's vtable
    #: entries occupy in instantiated class metadata.
    vtable_size: int = csd.csfield(cs.Int32ul)

    def get_vtable_offset(self, description: TargetClassContextDescriptor) -> int:
        if description.has_resilient_superclass():
            bounds = description.get_metadata_bounds()
            ptr = DirectPointer(Void)
            return (
                #: we have to pass fp because DirectPointer needs it
                bounds.immediate_members_offset / sizeof(ptr, fp=self._fp)
                + self.vtable_offset
            )
        return self.vtable_offset


@dc.dataclass
class TargetMethodDescriptor(Virtual):
    """An opaque descriptor describing a class or protocol method.

    References to these descriptors appear in the method override table of a
    class context descriptor, or a resilient witness table pattern, respectively.

    Clients should not assume anything about the contents of this descriptor
    other than it having 4 byte alignment.
    """

    #: Flags describing the method.
    flags_value: int = csd.csfield(cs.Int32ul)
    flags: MethodDescriptorFlags = csd.csfield(Flags(MethodDescriptorFlags))

    #: The method implementation.
    impl: RelativeDirectPointer[Void, Nullable] = csd.csfield(
        RelativeDirectPointer(Void, True)
    )


@dc.dataclass
class TargetOverrideTableHeader(Virtual):
    """Header for a class vtable override descriptor.

    This is a variable-sized structure that provides implementations for
    overrides of methods defined in superclasses.
    """

    #: The offset of the vtable for this class in its metadata, if any,
    #: in words.
    #:
    #: If this class has a resilient superclass, this offset is relative to the
    #: the start of the immediate class's metadata. Otherwise, it is relative
    #: to the metadata address point.
    num_entries: int = csd.csfield(cs.Int32ul)


#: Method descriptor pointer
TargetRelativeMethodDescriptorPointer = RelativeDirectPointer[
    TargetMethodDescriptor, Nullable
]


@dc.dataclass
class TargetMethodOverrideDescriptor(Virtual):
    """
    An entry in the method override table, referencing a method from one of our
    ancestor classes, together with an implementation.
    """

    #: The class containing the base method.
    decl_class: TargetRelativeContextPointer = csd.csfield(TargetRelativeContextPointer)
    #: The base method.
    method: TargetRelativeMethodDescriptorPointer = csd.csfield(
        RelativeDirectPointer(TargetMethodDescriptor, True)
    )
    #: The implementation of the override.
    impl: RelativeDirectPointer[Void, Nullable] = csd.csfield(
        RelativeDirectPointer(Void, True)
    )


@dc.dataclass
class TargetMetadata(Virtual):
    #: The kind. Only valid for non-class metadata; getKind() must be used to get
    #: the kind value.
    kind: MetadataKind = csd.tfield(MetadataKind, cs.Enum(cs.Int64ul, MetadataKind))


@dc.dataclass
class TargetCanonicalSpecializedMetadatasListCount(Virtual):
    count: int = csd.csfield(cs.Int32ul)


@dc.dataclass
class TargetCanonicalSpecializedMetadataAccessorsListEntry(Virtual):
    accessor: CompactFunctionPointer[Void, NotNull] = csd.csfield(
        CompactFunctionPointer(Void)
    )


@dc.dataclass
class TargetCanonicalSpecializedMetadatasListEntry(Virtual):
    metadata: RelativeDirectPointer[TargetMetadata, NotNull] = csd.csfield(
        RelativeDirectPointer(TargetMetadata)
    )


@dc.dataclass
class TargetTypeContextDescriptor(TargetContextDescriptor):
    #: The name of the type.
    name: RelativeDirectPointer[str, NotNull] = csd.csfield(
        RelativeDirectPointer(CString)
    )

    def get_mangled_name(self) -> str:
        return self.name.get(self._address + sizeof(TargetContextDescriptor))

    #: A pointer to the metadata access function for this type.
    #_
    #: The function type here is a stand-in. You should use getAccessFunction()
    #: to wrap the function pointer in an accessor that uses the proper calling
    #: convention for a given number of arguments.
    access_function_ptr: CompactFunctionPointer[Void, Nullable] = csd.csfield(
        CompactFunctionPointer(Void, True)
    )

    def get_access_function(self) -> int:
        base = self._address + sizeof(TargetContextDescriptor) + 4
        return applyRelativeOffset(base, self.access_function_ptr.relative_offset)

    #: A pointer to the field descriptor for the type, if any.
    fields: RelativeDirectPointer[FieldDescriptor, Nullable] = csd.csfield(
        RelativeDirectPointer(FieldDescriptor, True)
    )

    def is_reflectable(self) -> bool:
        return not self.fields.is_null()

    def get_fields(self) -> t.Optional[FieldDescriptor]:
        if not self.is_reflectable():
            return None

        address = self._address + sizeof(TargetContextDescriptor) + 8
        return self.fields.get(address)

    kind_flags: TypeContextDescriptorFlags = csd.csfield(
        cs.Computed(lambda ctx: TypeContextDescriptorFlags(ctx.flags.kind_flags))
    )

    def get_type_context_descriptor_flags(self):
        return self.kind_flags

    #: Does this type have non-trivial "singleton" metadata initialization?
    #:
    #: The type of the initialization-control structure differs by subclass,
    #: so it doesn't appear here.
    def has_singleton_meta_initialization(self) -> bool:
        return (
            self.get_type_context_descriptor_flags().meta_initialization
            == MetadataInitializationKind.SingletonMetadataInitialization
        )

    #: Does this type have "foreign" metadata initialization?
    def has_foreign_meta_initialization(self) -> bool:
        return (
            self.get_type_context_descriptor_flags().meta_initialization
            == MetadataInitializationKind.ForeignMetadataInitialization
        )

    def get_foreign_metadata_initialization(
        self,
    ) -> t.Optional[TargetForeignMetadataInitialization]:
        raise NotImplementedError("Must be implemented in a sub-class!")

    def get_singleton_metadata_initialization(
        self,
    ) -> t.Optional[TargetSingletonMetadataInitialization]:
        raise NotImplementedError("Must be implemented in a sub-class!")

    def get_full_generic_context_header(
        self,
    ) -> TargetTypeGenericContextDescriptorHeader:
        raise NotImplementedError("Must be implemented in a sub-class!")

    def get_generic_context_header(self) -> TargetGenericContextDescriptorHeader:
        return self.get_full_generic_context_header().base

    def has_canonical_metadata_prespecializations(self) -> bool:
        return self.kind_flags.has_canonical_metadata_prespecializations


class TargetTypeDescriptor(TargetTypeContextDescriptor):
    # private:
    def _num_target_canonical_specialized_metadatas_list_count(self) -> int:
        return int(self.has_canonical_metadata_prespecializations())

    def _num_target_canonical_specialized_metadatas_list_entry(self) -> int:
        if not self.has_canonical_metadata_prespecializations():
            return 0
        return self.getTrailingObject(
            Token[TargetCanonicalSpecializedMetadatasListCount]
        ).count

    def _num_target_canonical_specialized_metadata_accessors_list_entry(self) -> int:
        return self._num_target_canonical_specialized_metadatas_list_entry()

    def _num_target_singleton_metadata_initialization(self) -> int:
        return int(self.has_singleton_meta_initialization())

    def _num_target_foreign_metadata_initialization(self) -> int:
        return int(self.has_foreign_meta_initialization())

    def _num_target_type_generic_context_descriptor_header(self) -> int:
        return self.is_generic()

    # public:
    def get_full_generic_context_header(
        self,
    ) -> TargetTypeGenericContextDescriptorHeader:
        # Only applicable for classes that derive from TrailingObjects
        return self.getTrailingObject(Token[TargetTypeGenericContextDescriptorHeader])

    def get_foreign_metadata_initialization(
        self,
    ) -> t.Optional[TargetForeignMetadataInitialization]:
        if not self.has_foreign_meta_initialization():
            return None
        return self.getTrailingObject(Token[TargetForeignMetadataInitialization])

    def get_singleton_metadata_initialization(
        self,
    ) -> t.Optional[TargetSingletonMetadataInitialization]:
        if not self.has_singleton_meta_initialization():
            return None

        return self.getTrailingObject(Token[TargetSingletonMetadataInitialization])


@dc.dataclass
class TargetClassContextDescriptor(
    TargetTypeDescriptor,
    TrailingGenericContextObjects[
        # Support for generics (only if self.is_generic)
        TargetTypeGenericContextDescriptorHeader,
        *TargetGenericSignature,
        # additional trailing objects
        TargetResilientSuperclass,
        TargetForeignMetadataInitialization,
        TargetSingletonMetadataInitialization,
        TargetVTableDescriptorHeader,
        TargetMethodDescriptor,
        TargetOverrideTableHeader,
        TargetMethodOverrideDescriptor,
        TargetObjCResilientClassStubInfo,
        TargetCanonicalSpecializedMetadatasListCount,
        TargetCanonicalSpecializedMetadatasListEntry,
        TargetCanonicalSpecializedMetadataAccessorsListEntry,
    ],
):
    """Descriptor for a class context."""

    def get_resilient_superclass_reference_kind(self) -> TypeReferenceKind:
        return (
            self.get_type_context_descriptor_flags().resilient_superclass_reference_kind
        )

    #: The type of the superclass, expressed as a mangled type name that can
    #: refer to the generic arguments of the subclass type.
    super_class_type: RelativeDirectPointer[str, Nullable] = csd.csfield(
        RelativeDirectPointer(CString, True)
    )

    def get_super_class_type(self) -> t.Optional[str]:
        address = sizeof(TargetTypeContextDescriptor) + self._address
        return self.super_class_type.get(address)

    @dc.dataclass  #: UNION
    class MetadataSizeOrBounds:
        #: If this descriptor does not have a resilient superclass, this is the
        #: negative size of metadata objects of this class (in words).
        meta_negative_size_in_words: int = csd.csfield(cs.Int32ul)

        #: If this descriptor has a resilient superclass, this is a reference
        #: to a cache holding the metadata's extents.
        resilient_meta_bounds: RelativeDirectPointer[Void, Nullable] = csd.csfield(
            #: Points to TargetMetadataBounds
            RelativeDirectPointer(Void, Nullable)
        )

    #: union wrapper
    meta_or_resilient_bounds: MetadataSizeOrBounds = csd.csfield(
        # four bytes of space
        AlignedUnion(4, csd.DataclassStruct(MetadataSizeOrBounds, union=True))
    )

    @dc.dataclass  #: UNION
    class MetadataSizeOrFlags:
        #: If this descriptor does not have a resilient superclass, this is the
        #: positive size of metadata objects of this class (in words).
        meta_positive_size_in_words: int = csd.csfield(cs.Int32ul)

        #: Otherwise, these flags are used to do things like indicating
        #: the presence of an Objective-C resilient class stub.
        resilient_flags: int = csd.csfield(cs.Int32ul)

    #: union wrapper
    meta_or_resilient_flags: MetadataSizeOrFlags = csd.csfield(
        AlignedUnion(4, csd.DataclassStruct(MetadataSizeOrFlags, union=True))
    )

    #: The number of additional members added by this class to the class
    #: metadata.  This data is opaque by default to the runtime, other than
    #: as exposed in other members; it's really just
    #: NumImmediateMembers * sizeof(void*) bytes of data.
    #:
    #: Whether those bytes are added before or after the address point
    #: depends on areImmediateMembersNegative().
    num_immediate_members: int = csd.csfield(cs.Int32ul)

    def get_immediate_members_size(self) -> int:
        return self.num_immediate_members * 8  #: sizeof(void *)

    #: Are the immediate members of the class metadata allocated at negative
    #: offsets instead of positive?
    def are_immediate_members_negative(self) -> bool:
        return self.get_type_context_descriptor_flags().immediate_members_negative

    #: The number of stored properties in the class, not including its
    #: superclasses. If there is a field offset vector, this is its length.
    num_fields: int = csd.csfield(cs.Int32ul)

    #: The offset of the field offset vector for this class's stored
    #: properties in its metadata, in words. 0 means there is no field offset
    #: vector.
    #:
    #: If this class has a resilient superclass, this offset is relative to
    #: the size of the resilient superclass metadata. Otherwise, it is
    #: absolute.
    field_offset_vector_offset: int = csd.csfield(cs.Int32ul)

    def has_resilient_superclass(self) -> bool:
        return self.get_type_context_descriptor_flags().has_resilient_super_class

    def has_vtable(self) -> bool:
        return self.kind_flags.has_vtable

    def has_override_table(self) -> bool:
        return self.kind_flags.has_override_table

    # private:
    def _num_target_resilient_superclass(self) -> int:
        return int(self.has_resilient_superclass())

    def _num_target_v_table_descriptor_header(self) -> int:
        return int(self.kind_flags.has_vtable)

    def _num_target_method_descriptor(self) -> int:
        if not self.has_vtable():
            return 0
        return self.get_vtable_header().vtable_size

    def _num_target_override_table_header(self) -> int:
        return int(self.kind_flags.has_override_table)

    def _num_target_method_override_descriptor(self) -> int:
        if not self.has_override_table():
            return 0
        return self.get_override_table_header().num_entries

    def _num_target_obj_c_resilient_class_stub_info(self) -> int:
        return int(self.kind_flags.has_resilient_super_class)

    # public:
    def get_vtable_header(self) -> t.Optional[TargetVTableDescriptorHeader]:
        if not self.has_vtable():
            return None

        return self.getTrailingObject(Token[TargetVTableDescriptorHeader])

    def get_methods(self) -> t.List[TargetMethodDescriptor]:
        if not self.has_vtable():
            return []
        return list(self.getTrailingObjects(Token[TargetMethodDescriptor]))

    def get_override_table_header(self) -> t.Optional[TargetOverrideTableHeader]:
        if not self.has_override_table():
            return None
        return self.getTrailingObject(Token[TargetOverrideTableHeader])

    def get_override_methods(self) -> t.List[TargetMethodOverrideDescriptor]:
        if not self.has_override_table():
            return []
        return list(self.getTrailingObjects(Token[TargetMethodOverrideDescriptor]))

    def has_field_offset_vector(self) -> bool:
        return bool(self.field_offset_vector_offset)

    #: Given that this class is known to not have a resilient superclass,
    #: return the offset of its immediate members in words.
    def get_non_resilient_immediate_members_offset(self) -> int:
        assert not self.has_resilient_superclass()
        if self.are_immediate_members_negative():
            return -self.meta_or_resilient_bounds.meta_negative_size_in_words
        else:
            return (
                self.meta_or_resilient_flags.meta_positive_size_in_words
                - self.num_immediate_members
            )

    #: Given that this class is known to not have a resilient superclass,
    #: return the offset of its generic arguments in words.
    def get_non_resilient_generic_argument_offset(self) -> int:
        return self.get_non_resilient_immediate_members_offset()

    #: Return the offset of the start of generic arguments in the nominal
    #: type's metadata. The returned value is measured in words.
    def get_generic_argument_offset(self) -> int:
        if not self.has_resilient_superclass():
            return self.get_non_resilient_generic_argument_offset()
        raise NotImplementedError("No available for InProcess")


@dc.dataclass
class TargetStructContextDescriptor(
    TargetTypeDescriptor,
    TrailingGenericContextObjects[
        TargetTypeGenericContextDescriptorHeader,  # always present if is_generic
        *TargetGenericSignature,
        # additional trailing objects
        TargetForeignMetadataInitialization,
        TargetSingletonMetadataInitialization,
        TargetCanonicalSpecializedMetadatasListCount,
        TargetCanonicalSpecializedMetadatasListEntry,
        TargetCanonicalSpecializedMetadataAccessorsListEntry,
    ],
):
    """Descriptor for a struct context."""

    #: The number of stored properties in the struct.
    #: If there is a field offset vector, this is its length.
    num_fields: int = csd.csfield(cs.Int32ul)

    #: The offset of the field offset vector for this struct's stored
    #: properties in its metadata, if any. 0 means there is no field offset
    #: vector.
    field_offset_vector_offset: int = csd.csfield(cs.Int32ul)


@dc.dataclass
class TargetEnumContextDescriptor(
    TargetTypeDescriptor,
    TrailingGenericContextObjects[
        TargetTypeGenericContextDescriptorHeader,
        *TargetGenericSignature,
        # additional (optional) trailing objects
        TargetForeignMetadataInitialization,
        TargetSingletonMetadataInitialization,
        TargetCanonicalSpecializedMetadatasListCount,
        TargetCanonicalSpecializedMetadatasListEntry,
        TargetCanonicalSpecializedMetadataAccessorsListEntry,
    ],
):
    """Descriptor for an enum context."""

    #: The number of non-empty cases in the enum are in the low 24 bits;
    #: the offset of the payload size in the metadata record in words,
    #: if any, is stored in the high 8 bits.
    num_payload_cases_and_payload_size_offset: int = csd.csfield(cs.Int32ul)

    #: The number of empty cases in the enum.
    num_empty_cases: int = csd.csfield(cs.Int32ul)

    def get_num_payload_cases(self) -> int:
        return self.num_payload_cases_and_payload_size_offset & 0x00FFFFFF

    def get_num_cases(self) -> int:
        return self.get_num_payload_cases() + self.num_empty_cases

    def get_payload_size_offset(self) -> int:
        return (self.num_payload_cases_and_payload_size_offset & 0xFF000000) >> 24

    def has_payload_size_offset(self) -> bool:
        return self.get_payload_size_offset() != 0


@dc.dataclass
class TargetTypeMetadataLayoutPrefix:  # no address here
    """
    Prefix of a metadata header, containing a pointer to the
    type layout string.
    """

    layout_string: DirectPointer[str, NotNull] = csd.csfield(DirectPointer(CString))


@dc.dataclass
class TargetTypeMetadataHeaderBase:
    #: A pointer to the value-witnesses for this type.  This is only
    #: present for type metadata.
    value_witnesses: DirectPointer[Void, NotNull] = csd.csfield(DirectPointer(Void))


# The common structure of all type metadata.
@dc.dataclass
class TargetTypeMetadataHeader(
    TargetTypeMetadataHeaderBase,
    TargetTypeMetadataLayoutPrefix,
):
    pass


@dc.dataclass
class TargetMetadata(Virtual):
    #: The kind. Only valid for non-class metadata; getKind() must be used to get
    #: the kind value.
    kind: MetadataKind = csd.tfield(MetadataKind, cs.Enum(cs.Int64ul, MetadataKind))


#: The common structure of all metadata for heap-allocated types. A
#: pointer to one of these can be retrieved by loading the 'isa'
#: field of any heap object, whether it was managed by Swift or by
#: Objective-C.  However, when loading from an Objective-C object,
#: this metadata may not have the heap-metadata header, and it may
#: not be the Swift type metadata for the object's dynamic type.
TargetHeapMetadata = TargetMetadata


@dc.dataclass
class TargetAnyClassMetadata(TargetHeapMetadata):
    """
    The portion of a class metadata object that is compatible with
    all classes, even non-Swift ones.
    """

    #: The metadata for the superclass.  This is null for the root class.
    super_class: DirectPointer[Void, Nullable] = csd.csfield(DirectPointer(Void, True))

    #: Is this object a valid swift type metadata?  That is, can it be
    #: safely downcast to ClassMetadata?
    def is_type_metadata(self) -> bool:
        return True

    #: A different perspective on the same bit.
    def is_pure_objc(self) -> bool:
        return not self.is_type_metadata()


@dc.dataclass
class TargetClassMetadata(TargetAnyClassMetadata):
    """
    The structure of all class metadata.  This structure is embedded
    directly within the class's heap metadata structure and therefore
    cannot be extended without an ABI break.

    Note that the layout of this type is compatible with the layout of
    an Objective-C class.

    If the Runtime supports Objective-C interoperability, this class inherits
    from TargetAnyClassMetadataObjCInterop, otherwise it inherits from
    TargetAnyClassMetadata.
    """

    #: Swift-specific class flags.
    flags: ClassFlags = csd.tfield(ClassFlags, cs.Enum(cs.Int32ul, ClassFlags))

    #: The address point of instances of this type.
    instance_address_point: int = csd.csfield(cs.Int32ul)

    #: The required size of instances of this type.
    #: 'InstanceAddressPoint' bytes go before the address point;
    #: 'InstanceSize - InstanceAddressPoint' bytes go after it.
    instance_size: int = csd.csfield(cs.Int32ul)

    #: The alignment mask of the address point of instances of this type.
    instance_align_mask: int = csd.csfield(cs.Int16ul)

    #: Reserved for runtime use.
    reserved: int = csd.csfield(cs.Int16ul)

    #: The total size of the class object, including prefix and suffix
    #: extents.
    class_size: int = csd.csfield(cs.Int32ul)

    #: The offset of the address point within the class object.
    class_address_point: int = csd.csfield(cs.Int32ul)

    #: Description is by far the most likely field for a client to try
    #: to access directly, so we force access to go through accessors.
    # private:
    #: An out-of-line Swift-specific description of the type, or null
    #: if this is an artificial subclass.  We currently provide no
    #: supported mechanism for making a non-artificial subclass
    #: dynamically.
    description: DirectPointer[TargetClassContextDescriptor, Nullable] = csd.csfield(
        DirectPointer(TargetClassContextDescriptor, True)
    )


@dc.dataclass
class TargetResilientWitnessesHeader(Virtual):
    """
    Header containing information about the resilient witnesses in a
    protocol conformance descriptor.
    """

    num_witnesses: int = csd.csfield(cs.Int32ul)


@dc.dataclass
class TargetResilientWitness(Virtual):
    """
    The control structure of a generic or resilient protocol
    conformance witness.

    Resilient conformances must use a pattern where new requirements
    with default implementations can be added and the order of existing
    requirements can be changed.

    This is accomplished by emitting an order-independent series of
    relative pointer pairs, consisting of a protocol requirement together
    with a witness. The requirement is identified by an indirectable relative
    pointer to the protocol requirement descriptor.
    """

    requirement: RelativeIndirectablePointer[
        TargetProtocolRequirement, Nullable
    ] = csd.csfield(RelativeIndirectablePointer(TargetProtocolRequirement, True))

    impl: RelativeDirectPointer[Void, Nullable] = csd.csfield(
        RelativeDirectPointer(Void, True)
    )


@dc.dataclass
class TargetGenericWitnessTable(Virtual):
    """
    The control structure of a generic or resilient protocol
    conformance, which is embedded in the protocol conformance descriptor.

    Witness tables need to be instantiated at runtime in these cases:
    - For a generic conforming type, associated type requirements might be
    dependent on the conforming type.
    - For a type conforming to a resilient protocol, the runtime size of
    the witness table is not known because default requirements can be
    added resiliently.

    One per conformance.
    """

    #: The size of the witness table in words.  This amount is copied from
    #: the witness table template into the instantiated witness table.
    table_size_in_words: int = csd.csfield(cs.Int16ul)

    #: The amount of private storage to allocate before the address point,
    #: in words. This memory is zeroed out in the instantiated witness table
    #: template.
    #
    #: The low bit is used to indicate whether this witness table is known
    #: to require instantiation.
    private_size_in_words: int = csd.csfield(cs.Int16ul)

    #: The instantiation function, which is called after the template is copied.
    instantiator: CompactFunctionPointer[Void, Nullable] = csd.csfield(
        CompactFunctionPointer(Void, True)
    )

    #: Private data for the instantiator.  Out-of-line so that the rest
    #: of this structure can be constant. Might be null when building with
    #: -disable-preallocated-instantiation-caches.
    private_data: RelativeDirectPointer[Void, Nullable] = csd.csfield(
        RelativeDirectPointer(Void, True)
    )

    def get_private_size(self) -> int:
        return self.private_size_in_words >> 1

    #: This bit doesn't really mean anything. Currently, the compiler always
    #: sets it when emitting a generic witness table.
    def requires_instantiation(self) -> bool:
        return self.private_size_in_words & 1


@dc.dataclass
class TargetTypeReference(Virtual):  # UNION
    """A reference to a type."""

    #: A direct reference to a TypeContextDescriptor or ProtocolDescriptor.
    direct_type_descriptor: RelativeDirectPointer[
        TargetContextDescriptor, Nullable
    ] = csd.csfield(RelativeDirectPointer(TargetContextDescriptor, True))

    #: An indirect reference to a TypeContextDescriptor or ProtocolDescriptor.
    indirect_type_descriptor: RelativeIndirectPointer[
        TargetContextDescriptor, Nullable
    ] = csd.csfield(RelativeIndirectPointer(TargetContextDescriptor, True))

    #: An indirect reference to an Objective-C class.
    indirect_objc_class: RelativeIndirectPointer[
        TargetClassMetadata, Nullable
    ] = csd.csfield(RelativeIndirectPointer(TargetClassMetadata, True))

    #: A direct reference to an Objective-C class name.
    direct_objc_class_name: RelativeDirectPointer[str, Nullable] = csd.csfield(
        RelativeDirectPointer(CString, True)
    )

    def get_type_descriptor(
        self, kind: TypeReferenceKind
    ) -> t.Optional[TargetContextDescriptor]:
        # TODO: explain why +4 here
        if kind == TypeReferenceKind.DirectTypeDescriptor:
            return self.direct_type_descriptor.get(self._address + 4)
        elif kind == TypeReferenceKind.IndirectTypeDescriptor:
            return self.indirect_type_descriptor.get(self._address + 4)

        return None


@dc.dataclass
class TargetWitnessTable:
    """A witness table for a protocol.

    With the exception of the initial protocol conformance descriptor,
    the layout of a witness table is dependent on the protocol being
    represented.
    """

    #: The protocol conformance descriptor from which this witness table
    #: was generated.
    description: DirectPointer[
        TargetProtocolConformanceDescriptor, Nullable
    ] = csd.csfield(DirectPointer(lambda: TargetProtocolConformanceDescriptor))


@dc.dataclass
class TargetProtocolConformanceDescriptor(
    Virtual,
    TrailingObjects[
        TargetRelativeContextPointer,
        TargetGenericRequirementDescriptor,  #: array
        GenericPackShapeDescriptor,  #: array
        TargetResilientWitnessesHeader,
        TargetResilientWitness,
        TargetGenericWitnessTable,
    ],
):
    """The structure of a protocol conformance.

    This contains enough static information to recover the witness table for a
    type's conformance to a protocol.
    """

    #: The protocol being conformed to.
    protocol: RelativeIndirectablePointer[
        TargetProtocolContextDescriptor, Nullable
    ] = csd.csfield(RelativeIndirectablePointer(TargetProtocolContextDescriptor, True))

    def get_protocol(self) -> t.Optional[TargetProtocolContextDescriptor]:
        return self.protocol.get(self._address)

    #: Some description of the type that conforms to the protocol.
    type_ref: TargetTypeReference = csd.csfield(
        AlignedUnion(4, csd.DataclassStruct(TargetTypeReference, union=True))
    )

    def get_type_descriptor(self) -> t.Optional[TargetContextDescriptor]:
        return self.type_ref.get_type_descriptor(self.flags.kind)

    #: The witness table pattern, which may also serve as the witness table.
    witness_table_pattern: RelativeDirectPointer[
        TargetWitnessTable, Nullable
    ] = csd.csfield(RelativeDirectPointer(TargetWitnessTable, True))

    #: Various flags, including the kind of conformance.
    flags_value: int = csd.csfield(cs.Int32ul)
    flags: ConformanceFlags = csd.csfield(
        cs.Computed(lambda ctx: ConformanceFlags(ctx.flags_value))
    )

    # public:
    def has_conditional_requirements(self) -> bool:
        return bool(self.flags.num_conditional_requirements)

    #: Retrieve the conditional requirements that must also be
    def get_conditional_requirements(
        self,
    ) -> t.List[TargetGenericRequirementDescriptor]:
        if not self.has_conditional_requirements():
            return []
        return list(self.getTrailingObjects(Token[TargetGenericRequirementDescriptor]))

    #: Retrieve the pack shape descriptors for the conditional pack requirements.
    def get_conditional_requirements(
        self,
    ) -> t.List[TargetGenericRequirementDescriptor]:
        if not self.flags.num_conditional_pack_shape_descriptors:
            return []
        return list(self.getTrailingObjects(Token[GenericPackShapeDescriptor]))

    #: Retrieve the resilient witnesses.
    def get_resilient_witnesses(self) -> t.List[TargetResilientWitness]:
        if self._num_target_resilient_wittness() == 0:
            return []
        return list(self.getTrailingObjects(Token[TargetResilientWitness]))

    # private:
    def _num_target_relative_context_pointer(self) -> int:
        return int(self.flags.retroactive)

    def _num_target_generic_requirement_descriptor(self) -> int:
        return self.flags.num_conditional_requirements

    def _num_generic_pack_shape_descriptor(self) -> int:
        return self.flags.num_conditional_pack_shape_descriptors

    def _num_target_resilient_witnesses_header(self) -> int:
        return int(self.flags.has_resilient_witnesses)

    def _num_target_resilient_wittness(self) -> int:
        if not self.flags.has_resilient_witnesses:
            return 0
        return self.getTrailingObject(
            Token[TargetResilientWitnessesHeader]
        ).num_witnesses

    def _num_target_generic_witness_table(self) -> int:
        return int(self.flags.has_generic_witness_table)
