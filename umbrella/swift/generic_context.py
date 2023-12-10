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

import typing as t

import dataclasses as dc
import construct as cs
import construct_dataclasses as csd

from umbrella.runtime import RawCString, Virtual, AlignedUnion, sizeof
from umbrella.flags import from_flags, Flags
from umbrella.trailing_objects import TrailingObjects, TrailingTys
from umbrella.swift import (
    RelativeDirectPointer,
    RelativeIndirectablePointerIntPair,
    RelativeIndirectablePointer,
    NotNull,
    Nullable,
    GenericPackKind,
    GenericParamKind,
    GenericRequirementFlags,
    GenericRequirementKind,
)
from umbrella import swift


@dc.dataclass
class TargetGenericContextDescriptorHeader:
    # The number of (source-written) generic parameters, and thus
    # the number of GenericParamDescriptors associated with this
    # context.  The parameter descriptors appear in the order in
    # which they were given in the source.
    #
    # A GenericParamDescriptor corresponds to a type metadata pointer
    # in the arguments layout when isKeyArgument() is true.
    # isKeyArgument() will be false if the parameter has been made
    # equivalent to a different parameter or a concrete type.
    num_params: int = csd.csfield(cs.Int16ul)

    # The number of GenericRequirementDescriptors in this generic
    # signature.
    #
    # A GenericRequirementDescriptor of kind Protocol corresponds
    # to a witness table pointer in the arguments layout when
    # isKeyArgument() is true.  isKeyArgument() will be false if
    # the protocol is an Objective-C protocol.  (Unlike generic
    # parameters, redundant conformance requirements can simply be
    # eliminated, and so that case is not impossible.)
    num_requirements: int = csd.csfield(cs.Int16ul)

    # The size of the "key" area of the argument layout, in words.
    # Key arguments include shape classes, generic parameters and
    # conformance requirements which are part of the identity of
    # the context.
    #
    # The key area of the argument layout consists of:
    #
    # - a sequence of pack lengths, in the same order as the parameter
    #   descriptors which satisfy getKind() == GenericParamKind::TypePack
    #   and hasKeyArgument();
    #
    # - a sequence of metadata or metadata pack pointers, in the same
    #   order as the parameter descriptors which satisfy hasKeyArgument();
    #
    # - a sequence of witness table or witness table pack pointers, in the
    #   same order as the requirement descriptors which satisfy
    #   hasKeyArgument().
    #
    # The elements above which are packs are precisely those appearing
    # in the sequence of trailing GenericPackShapeDescriptors.
    num_key_args: int = csd.csfield(cs.Int16ul)

    # Originally this was the size of the "extra" area of the argument
    # layout, in words.  The idea was that extra arguments would
    # include generic parameters and conformances that are not part
    # of the identity of the context; however, it's unclear why we
    # would ever want such a thing.  As a result, in pre-5.8 runtimes
    # this field is always zero.  New flags can only be added as long
    # as they remains zero in code which must be compatible with
    # older Swift runtimes.
    flags: int = csd.csfield(cs.Int16ul)

    def get_num_arguments(self) -> int:
        # Note: this used to be NumKeyArguments + NumExtraArguments,
        # and flags was named NumExtraArguments, which is why Flags
        # must remain zero when backward deploying to Swift 5.7 or
        # earlier.
        return self.num_key_args + self.flags

    def has_arguments(self) -> bool:
        return self.get_num_arguments() > 0

    def has_type_packs(self) -> bool:
        return bool(self.flags & 0x1)


@dc.dataclass
class TargetGenericRequirementDescriptor(Virtual):
    flags_value: int = csd.csfield(cs.Int32ul)
    flags: GenericRequirementFlags = csd.csfield(
        Flags(GenericRequirementFlags, "flags_value")
    )

    # The type that's constrained, described as a mangled name. (symbolic ref)
    param: RelativeDirectPointer[RawCString, NotNull] = csd.csfield(
        RelativeDirectPointer(RawCString)
    )

    @dc.dataclass
    class TypeRef:
        # A mangled representation of the same-type or base class the param is
        # constrained to. (RelativePointer<string>)
        #
        # Only valid if the requirement has SameType or BaseClass kind.
        type: RelativeDirectPointer[RawCString, NotNull] = csd.csfield(
            RelativeDirectPointer(RawCString)
        )

        # The protocol the param is constrained to.
        # (RelativePointer<protocol_descriptor_t>)
        #
        # Only valid if the requirement has Protocol kind.
        protocol: RelativeIndirectablePointerIntPair[t.Any, Nullable] = csd.csfield(
            RelativeIndirectablePointerIntPair(lambda: swift.TargetProtocolContextDescriptor, True)
        )

        # The conformance the param is constrained to use.
        # (RelativePointer<protocol_conformance_descriptor_t>)
        #
        # Only valid if the requirement has SameConformance kind.
        conformance: RelativeIndirectablePointer[t.Any, NotNull] = csd.csfield(
            RelativeIndirectablePointer(
                lambda: swift.TargetProtocolConformanceDescriptor, False
            )
        )

        # The kind of layout constraint. (uint32_t)
        #
        # Only valid if the requirement has Layout kind.
        layout: int = csd.csfield(cs.Int32ul)

    # the packed value
    value: TypeRef = csd.csfield(
        AlignedUnion(4, csd.DataclassStruct(TypeRef, union=True))
    )

    def has_param(self) -> bool:
        return not self.param.is_null()

    def get_kind(self) -> GenericRequirementKind:
        return self.flags.kind

    def get_param(self) -> bytes:
        address = self._address + 4  # sizeof(Int32ul)
        return self.param.get(address)

    def has_known_kind(self) -> bool:
        """Determine whether this generic requirement has a known kind.

        :return: returns false for any future generic requirement kinds.
        :rtype: bool
        """
        return isinstance(self.get_kind(), GenericRequirementKind)

    def get_protocol(self) -> "swift.TargetProtocolContextDescriptor":
        """Retrieve the protocol for a Protocol requirement."""
        assert self.get_kind() == GenericRequirementKind.Protocol
        return self.value.protocol.get(self._address + 8)

    def get_mangled_typename(self) -> t.Optional[bytes]:
        """Retrieve the right-hand type for a SameType, BaseClass or SameShape requirement."""
        kind = self.get_kind()
        assert kind in (
            GenericRequirementKind.Sametype,
            GenericRequirementKind.Baseclass,
            GenericRequirementKind.SameShape,
        ), "Invalid requirement kind!"
        return self.value.type.get(self._address + 8)

    def get_layout(self) -> int:
        """Retrieve the layout constraint."""
        assert self.get_kind() == GenericRequirementKind.Layout
        return self.value.layout

    def get_conformance(self) -> "swift.TargetProtocolConformanceDescriptor":
        """
        Retrieve the protocol conformance record for a SameConformance
        requirement.
        """
        assert self.get_kind() == GenericRequirementKind.SameConformance
        return self.value.conformance.get(self._address + 8)


@dc.dataclass  # not virtual, see get_generic_pack_shape_header
class GenericPackShapeHeader:
    # The number of generic parameters and conformance requirements
    # which are packs.
    #
    # Must equal the sum of:
    # - the number of GenericParamDescriptors whose kind is
    #   GenericParamKind::TypePack and isKeyArgument bits set;
    # - the number of GenericRequirementDescriptors with the
    #   isPackRequirement and isKeyArgument bits set
    num_packs: int = csd.csfield(cs.Int16ul)

    # The number of equivalence classes in the same-shape relation.
    num_shape_classes: int = csd.csfield(cs.Int16ul)


@dc.dataclass
class GenericPackShapeDescriptor:
    """
    The GenericPackShapeHeader is followed by an array of these descriptors,
    whose length is given by the header's NumPacks field.

    The invariant is that all pack descriptors with ``GenericPackKind::Metadata``
    must precede those with ``GenericPackKind::WitnessTable``, and for each kind,
    the pack descriptors are ordered by their Index.

    This allows us to iterate over the generic arguments array in parallel
    with the array of pack shape descriptors. We know we have a metadata
    or witness table when we reach the generic argument whose index is
    stored in the next descriptor; we increment the descriptor pointer in
    this case.
    """

    kind: GenericPackKind = csd.tfield(
        GenericPackKind, cs.Enum(cs.Int16ul, GenericPackKind)
    )

    # The index of this metadata pack or witness table pack in the
    # generic arguments array.
    index: int = csd.csfield(cs.Int16ul)

    # The equivalence class of this pack under the same-shape relation.
    #
    # Must be less than GenericPackShapeHeader::NumShapeClasses.
    shape_class: int = csd.csfield(cs.Int16ul)
    unused: int = csd.csfield(cs.Int16ul)


@dc.dataclass
class GenericParamDescriptor:
    # Don't set 0x40 for compatibility with pre-Swift 5.8 runtimes
    value: int = csd.csfield(cs.Int8ul)
    kind: GenericParamKind = csd.csfield(
        cs.Computed(lambda ctx: from_flags(GenericParamKind, ctx.value, 0x3F))
    )

    def has_key_argument(self) -> bool:
        return (self.value & 0x80) != 0

    # The default parameter descriptor for an implicit parameter.
    def is_implicit(self) -> bool:
        return self.kind == GenericParamKind.Type and self.has_key_argument()


HeaderTy = t.TypeVar("HeaderTy")


# A runtime description of a generic signature.
@dc.dataclass(frozen=True)
class RuntimeGenericSignature:
    header: TargetGenericContextDescriptorHeader
    params: t.List[GenericParamDescriptor]
    requirements: t.List[TargetGenericRequirementDescriptor]
    pack_shape_header: GenericPackShapeHeader
    pack_shape_descriptors: t.List[GenericPackShapeDescriptor]

# REVISIT: use container type that stores all data which then can be
# used to parse the generic parameters
TargetGenericSignature = (
    GenericParamDescriptor,
    TargetGenericRequirementDescriptor,
    GenericPackShapeHeader,
    GenericPackShapeDescriptor,
)
"""
Contents of a runtime gneric signature. This constant tuple can be
used to reduce the hand-written argument s within a class definition.

The following trailing objects will be added if you use ``*TargetGenericSignature``:

- ``GenericParamDescriptor``,
- ``TargetGenericRequirementDescriptor``,
- ``GenericPackShapeHeader`` and
- ``GenericPackShapeDescriptor``

Example:

>>> class Foo(TrailingObjects[Bar, *TargetGenericSignature, Baz]): ...
"""


# This oddity with partial specialization is necessary to get
# reasonable-looking code while also working around various kinds of
# compiler bad behavior with injected class names.
class TrailingGenericContextObjects(
    TrailingObjects[
        HeaderTy,
        # TODO: rework TrailingObjects to accept this
        # GenericParamDescriptor,
        # TargetGenericRequirementDescriptor,
        # GenericPackShapeHeader,
        # GenericPackShapeDescriptor,
        *TrailingTys,
    ],
):
    """
    Partial specialization of TrailingObjects that defines default functions
    for generic types.
    """

    # NOTE: This attribute is used within the TrailingObjects class
    # to indicate that this class specifies the type arguments.
    __generic_root__ = True

    def get_generic_context_header(self) -> HeaderTy:
        """Returns the generic context header of this type.

        :return: the parsed header
        :rtype: HeaderTy
        """
        header_ty = self.__trailing__[0]
        return self.getTrailingObjects(header_ty)

    def _num_target_generic_context_descriptor_header(self, fp) -> int:
        # Even though the header type is generic, this struct is supported
        # by default
        return int(self.is_generic())

    def get_generic_context(self) -> t.Optional[TargetGenericContext]:
        """Returns the generic context of this type context.

        :return: the parsed generic context
        :rtype: t.Optional[TargetGenericContext]
        """
        if not self.is_generic():
            return None

        # The generic context header should always be immediately followed in
        # memory by trailing parameter and requirement descriptors.
        header = self.get_generic_context_header()
        assert hasattr(header, "_address"), "Invalid header type - no address found"

        offset = header._address - sizeof(TargetGenericContext)
        return self._fp.read_struct(TargetGenericContext, offset)

    def get_generic_params(self) -> t.List[GenericParamDescriptor]:
        """Returns the list of generic parameters in the signature.

        :return: never null, always a list of parameters
        :rtype: t.List[GenericParamDescriptor]
        """
        if not self.is_generic():
            return []
        # Using '_num_generic_param_descriptor' to determine the size
        # of the internal array, this method will result in a tuple
        params = list(self.getTrailingObjects(GenericParamDescriptor))
        header = self.get_generic_context_header()
        return params[:header.num_params]

    def _num_generic_param_descriptor(self) -> int:
        if not self.is_generic():
            return 0

        header = self.get_generic_context_header()
        # NOTE: it has been observed that sometimes there are
        # key arguments at the end of original type parameters.
        # In conclusion, it is more safe to use.num_key_args
        # together with .num_params
        num_params = header.num_params
        if header.num_key_args > num_params:
            num_params += header.num_key_args - num_params
        return num_params

    def get_generic_requirements(
        self,
    ) -> t.List[TargetGenericRequirementDescriptor]:
        """Returns all generic requirements as a list.

        :return: the generic requirements as a list
        :rtype: t.List[TargetGenericRequirementDescriptor]
        """
        if not self.is_generic():
            return []

        return list(self.getTrailingObjects(TargetGenericRequirementDescriptor))

    def _num_target_generic_requirement_descriptor(self) -> int:
        return (
            0
            if not self.is_generic()
            else self.get_generic_context_header().num_requirements
        )

    def get_generic_pack_shape_header(self) -> GenericPackShapeHeader:
        """Returns the generic pack shape header of this context.

        :return: the pack shape header if present
        :rtype: GenericPackShapeHeader
        """
        if not self.is_generic():
            return GenericPackShapeHeader(0, 0)

        context_head = self.get_generic_context_header()
        if not context_head.has_type_packs():
            # Additional check, just return an empty header
            return GenericPackShapeHeader(0, 0)

        return self.getTrailingObjects(GenericPackShapeHeader)

    def _num_generic_pack_shape_header(self) -> int:
        return int(self.is_generic())

    def get_generic_pack_shape_descriptors(self) -> t.List[GenericPackShapeDescriptor]:
        """Returns all pack shape descriptors

        :return: _description_
        :rtype: t.List[GenericPackShapeDescriptor]
        """
        header = self.get_generic_pack_shape_header()
        if header.num_packs == 0:
            return []

        return list(self.getTrailingObjects(GenericPackShapeDescriptor))

    def _num_generic_pack_shape_descriptor(self) -> int:
        return (
            0
            if not self.is_generic()
            else self.get_generic_pack_shape_header().num_packs
        )

    def get_generic_signature(self) -> t.Optional[RuntimeGenericSignature]:
        """Creates a runtime generic signature if this descriptor is generic.

        :return: the runtime signature
        :rtype: t.Optional[RuntimeGenericSignature]
        """
        if not self.is_generic():
            return None

        return RuntimeGenericSignature(
            self.get_generic_context_header(),
            self.get_generic_params(),
            self.get_generic_requirements(),
            self.get_generic_pack_shape_header(),
            self.get_generic_pack_shape_descriptors(),
        )


@dc.dataclass
class TargetGenericContext(
    Virtual, TrailingGenericContextObjects[TargetGenericContextDescriptorHeader]
):
    """Dummy generic context class"""

    def is_generic(self) -> bool:
        return True
