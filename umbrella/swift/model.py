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
import typing as t
from lief import Function, Binary

from umbrella.swift import (
    TargetContextDescriptor,
    TargetProtocolContextDescriptor,
    TargetProtocolConformanceDescriptor,
    BuiltinTypeDescriptor,
    AssociatedTypeDescriptor,
    DynamicSwiftSectionIterator,
    SwiftSectionIterator,
    TargetMethodDescriptor,
    FieldRecord,
    TargetClassContextDescriptor,
    MethodDescriptorKind,
    ReflectionSectionKind,
    ContextDescriptorKind,
    TargetEnumContextDescriptor,
    TargetStructContextDescriptor,
)
from umbrella.runtime import Runtime


class SwiftTypeCache(SwiftSectionIterator[TargetContextDescriptor]):
    kind = "typemd"

    def _load_at(self, address: int) -> TargetContextDescriptor:
        descriptor = super()._load_at(address)
        # This method automatically infers the right context
        # type and returns null on failure
        return descriptor.cast()


class SwiftProtocolCache(SwiftSectionIterator[TargetProtocolContextDescriptor]):
    kind = "protocs"


class SwiftProtocolConformanceCache(
    SwiftSectionIterator[TargetProtocolConformanceDescriptor]
):
    kind = "conform"


class SwiftBuiltinTypeCache(DynamicSwiftSectionIterator[BuiltinTypeDescriptor]):
    kind = "builtin"


class SwiftAssociatedTypesCache(DynamicSwiftSectionIterator[AssociatedTypeDescriptor]):
    kind = "assocty"

    def _current_size(self, obj: AssociatedTypeDescriptor) -> int:
        base_size = super()._current_size(obj)
        return base_size + (obj.num_associated_types * obj.type_record_size)


def _filter_by_kind(iterable: t.Iterable, kind) -> filter:
    return filter(lambda x: x.get_kind() == kind, iterable)

class ReflectionContext(Runtime):
    def __init__(self, __binary) -> None:
        super().__init__(__binary)
        self._types = SwiftTypeCache(self)
        self._protos = SwiftProtocolCache(self)
        self._conform = SwiftProtocolConformanceCache(self)
        self._builtin = SwiftBuiltinTypeCache(self)
        self._assocty = SwiftAssociatedTypesCache(self)
        self._functions = {x.address: x for x in self.binary.functions}

    @property
    def types(self) -> SwiftTypeCache:
        return self._types

    @property
    def protos(self) -> SwiftProtocolCache:
        return self._protos

    def classes(self) -> t.Iterator[TargetClassContextDescriptor]:
        # NOTE: we have reset the type iterator in order to include all
        # classes. There will be no extra parsing as the class was already
        # parsed (and cached).
        self.types.pos = self.types.RESET
        return _filter_by_kind(self.types, ContextDescriptorKind.Class)

    def enums(self) -> t.Iterator[TargetEnumContextDescriptor]:
        self.types.pos = self.types.RESET
        return _filter_by_kind(self.types, ContextDescriptorKind.Enum)

    def structs(self) -> t.Iterator[TargetStructContextDescriptor]:
        self.types.pos = self.types.RESET
        return _filter_by_kind(self.types, ContextDescriptorKind.Struct)

    def get_function(self, address: int) -> t.Optional[Function]:
        return self._functions.get(address, None)

    def match_class_methods(
        self,
        cls: TargetClassContextDescriptor,
        cb: t.Callable[[TargetMethodDescriptor, FieldRecord], None],
        **kwargs
    ) -> None:
        if not cls.has_vtable():
            return

        if not cls.is_reflectable():
            # Make sure on all methods will be operated
            fields = []
        else:
            fd = cls.get_fields()
            # 1. Filter out all non-var related fields
            fields = list(filter(lambda x: x.is_var(), fd.get_fields()))

        index = 0
        current_methods = []
        for method in cls.get_methods():
            if method._address in self._functions or index >= len(fields):
                # Ignore publicly available fields
                cb(method, None, **kwargs)
                continue

            # No methods: the first occurrence must be a Getter
            if (
                len(current_methods) == 0
                and method.flags.kind == MethodDescriptorKind.Getter
            ):
                current_methods.append(method)
                continue

            # One Getter: the second method must be of type Setter
            if (
                len(current_methods) == 1
                and method.flags.kind == MethodDescriptorKind.Setter
            ):
                current_methods.append(method)
                continue

            # Getter and Setter: only the modify coroutine is missing
            if (
                len(current_methods) == 2
                and method.flags.kind == MethodDescriptorKind.ModifyCoroutine
            ):
                current_methods.append(method)
                field = fields[index]
                for current_method in current_methods:
                    cb(current_method, field, **kwargs)
                index += 1
            else:
                cb(method, None, **kwargs)

            current_methods.clear()

def has_swift_metadata(binary: Binary) -> bool:
    names = map(lambda x: x.value, ReflectionSectionKind)
    sections = list(map(lambda x: x.name, binary.sections))

    for section_name in names:
        if section_name in sections:
            return True

    return False