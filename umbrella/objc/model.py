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

import typing as t
import construct as cs
import lief

from umbrella.objc import (
    # model classes
    BoundListIterator,
    ObjCMethod,
    ObjCIVar,
    # structs
    TargetIVarList,
    TargetPropertyList,
    TargetMethodList,
    TargetProtocolList32,
    TargetProtocolList64,
    TargetProtocolRaw32,
    TargetProtocolRaw64,
    TargetIVarRaw32,
    TargetIVarRaw64,
    TargetPropertyRaw32,
    TargetPropertyRaw64,
    TargetMethodRaw32,
    TargetMethodRaw64,
    TargetObjCClassRaw32,
    TargetObjCClassRaw64,
    TargetClassDataRaw32,
    TargetClassDataRaw64,
    TargetSwiftClassRaw32,
    TargetSwiftClassRaw64,
    TargetCategoryRaw32,
    TargetCategoryRaw64,
    TargetSmallMethodRaw,
    # types
    RawClassT,
    RawClassDataT,
    RawSwiftClassT,
    RawCategoryT,
)
from umbrella.objc.base import (
    ObjCIVar,
    ObjCMethod,
    ObjCProperty,
    ObjCProtocol,
    ObjCClass,
    ObjCCategory,
)
from umbrella.runtime import Runtime, sizeof, CString
from umbrella.iterator import ReflectionSectionIterator


class SelectorCache(ReflectionSectionIterator[str]):
    kind = "__objc_selrefs"
    struct = CString


class IVarIterator(BoundListIterator[ObjCIVar]):
    @staticmethod
    def get_instance(runtime: Runtime, address: int, parent=None) -> IVarIterator:
        p_struct = TargetIVarRaw64 if runtime.is_64() else TargetIVarRaw32
        lst = runtime.read_struct(TargetIVarList, address)
        return IVarIterator(runtime, parent=parent, lst=lst, struct=p_struct)

    def _base_address(self, __address: int) -> int:
        return __address + sizeof(TargetIVarList)

    def _load_list_element(self, raw_address: int, context: cs.Container) -> ObjCIVar:
        struct = context.struct
        raw = self.runtime.read_struct(struct, raw_address)

        name = self.runtime.read_string(raw.name, fix=True)
        type_name = self.runtime.read_string(raw.type, fix=True)

        # Swap type names if necessary
        if type_name and name:
            name, type_name = self._swap_names(name, type_name)

        return ObjCIVar(raw, name, type_name, context.parent)

    def _swap_names(self, name: str, type_name: str) -> t.Tuple[str, str]:
        # Somtimes these names have to be swapped???
        if type_name[0] == "_" or name[0] == "T" or len(name) <= 2:
            type_name, name = name, type_name

        return name, type_name


class MethodIterator(BoundListIterator[ObjCMethod]):
    @staticmethod
    def get_instance(
        runtime: Runtime, address: int, parent=None, class_context=False
    ) -> MethodIterator:
        p_struct = TargetMethodRaw64 if runtime.is_64() else TargetMethodRaw32
        lst = runtime.read_struct(TargetMethodList, address)
        return MethodIterator(
            runtime,
            parent=parent,
            lst=lst,
            struct=p_struct,
            class_context=class_context,
        )

    def _preload_context(self, **kwds) -> None:
        super()._preload_context(**kwds)
        self.context.class_context = kwds.get("class_context", False)
        self.context.is_small = (self.context.lst.flags() & 0x80000000) != 0

    def _base_address(self, __address: int) -> int:
        return __address + sizeof(TargetMethodList)

    def _load_list_element(self, raw_address: int, context: cs.Container) -> ObjCMethod:
        struct = context.struct
        # Parse raw method
        if self.context.is_small:
            raw = self.runtime.read_struct(TargetSmallMethodRaw, raw_address)
            name = self.runtime.read_string(raw_address + raw.name)
            signature = self.runtime.read_string(raw_address + 4 + raw.signature)
        else:
            raw = self.runtime.read_struct(struct, raw_address)
            name = self.runtime.read_string(raw.name, fix=True)
            signature = self.runtime.read_string(raw.signature, fix=True)

        return ObjCMethod(
            raw,
            name,
            signature,
            is_class_method=context.class_context,
            is_small=context.is_small,
        )


class PropertyIterator(BoundListIterator[ObjCProperty]):
    @staticmethod
    def get_instance(runtime: Runtime, address: int, parent=None):
        p_struct = TargetPropertyRaw64 if runtime.is_64() else TargetPropertyRaw32
        lst = runtime.read_struct(TargetPropertyList, address)
        return PropertyIterator(runtime, parent=parent, lst=lst, struct=p_struct)

    def _base_address(self, __address: int) -> int:
        return __address + sizeof(TargetPropertyList)

    def _load_list_element(
        self, raw_address: int, context: cs.Container
    ) -> ObjCProperty:
        struct = context.struct
        raw = self.runtime.read_struct(struct, raw_address)

        name = self.runtime.read_string(raw.name)
        attributes = self.runtime.read_string(raw.attributes)
        return ObjCProperty(raw, name, attributes, context.parent)


class ProtocolIterator(BoundListIterator[ObjCProtocol]):
    @staticmethod
    def get_instance(runtime, address: int, parent=None):
        lst_struct = TargetProtocolList64 if runtime.is_64() else TargetProtocolList32
        p_struct = TargetProtocolRaw64 if runtime.is_64() else TargetProtocolRaw32

        lst = runtime.read_struct(lst_struct, address)
        return ProtocolIterator(runtime, parent=parent, lst=lst, struct=p_struct)

    @staticmethod
    def global_instance(runtime: Runtime) -> ProtocolIterator:
        section = runtime.binary.get_section("__objc_protolist")
        struct = cs.Int64ul if runtime.is_64() else cs.Int32ul

        ptrs = runtime.pointers("__objc_protolist", struct=struct)
        cls = TargetProtocolList32
        p_struct = TargetProtocolRaw64 if runtime.is_64() else TargetProtocolRaw32
        if runtime.is_64():
            cls = TargetProtocolList64

        # Simulate a protocol list by creating a plain instance
        lst = cls(count=len(ptrs))
        lst._address = section.virtual_address if section else 0
        lst._fp = runtime
        return ProtocolIterator(
            runtime, lst=lst, ptrs=ptrs, parent=None, struct=p_struct
        )

    def _preload_context(self, **kwds) -> None:
        self.context.ptrs = kwds.get("ptrs")
        super()._preload_context(**kwds)
        if self.context.ptrs is None:
            # Parse all relevant pointers
            word = cs.Int64ul if self._is_arch64() else cs.Int32ul
            address = self.context.address
            struct = cs.Array(self.context.count, word)
            self.context.ptrs = list(self.runtime.read_struct(struct, address))

    def _is_arch64(self) -> bool:
        return self.runtime.is_64()

    def _base_address(self, __address: int) -> int:
        if self.context.ptrs:
            # TODO: explain why we need the plain address here
            return __address
        cls = TargetProtocolList32
        if self._is_arch64():
            cls = TargetProtocolList64
        return __address + sizeof(cls)

    def _get_address(self, pos: int) -> int:
        return self.context.ptrs[pos]

    def _load_list_element(
        self, raw_address: int, context: cs.Container
    ) -> ObjCProtocol:
        ctx = self.context
        raw = self.runtime.read_struct(ctx.struct, raw_address)

        name = self.runtime.read_string(raw.name)
        protocol = ObjCProtocol(raw, name, parent=ctx.parent)
        if raw.protocols:
            protocol.protocols = ProtocolIterator.get_instance(
                self.runtime, raw.protocols, protocol
            )

        if raw.instance_properties:
            protocol.instance_properties = PropertyIterator.get_instance(
                self.runtime, raw.instance_properties, protocol
            )

        for name in ("optional_class_methods", "required_class_methods"):
            ptr = getattr(raw, name)
            if ptr:
                iterator = MethodIterator.get_instance(
                    self.runtime,
                    ptr,  # starting address
                    protocol,  # parent
                    class_context=True,  # class methods?
                )
                setattr(protocol, name, iterator)

        for name in ("optional_instance_methods", "required_instance_methods"):
            ptr = getattr(raw, name)
            if ptr:
                iterator = MethodIterator.get_instance(
                    self.runtime,
                    ptr,  # starting address
                    protocol,  # parent
                    class_context=False,  # class methods?
                )
                setattr(protocol, name, iterator)

        return protocol


class ClassIterator(ReflectionSectionIterator[ObjCClass]):
    kind = "__objc_classlist"

    def __init__(self, __runtime: Runtime) -> None:
        # NOTE: we have to place this attribute definition before calling
        # super() as we want to skip type inspection
        is_64 = __runtime.is_64()
        self.struct = TargetObjCClassRaw64 if is_64 else TargetObjCClassRaw32
        super().__init__(__runtime, pointer_ty=cs.Int64ul if is_64 else cs.Int32ul)
        # prepare format hint
        self.context.is_64 = is_64

    def _load_at(self, address: int, parent_address=0) -> ObjCClass:
        raw: RawClassT = super()._load_at(address)
        ctx = self.context

        data_struct = TargetClassDataRaw64 if ctx.is_64 else TargetClassDataRaw32
        raw_data: RawClassDataT = self.runtime.read_struct(data_struct, raw.data.ptr)

        if raw.data.is_swift():
            cls_struct = TargetSwiftClassRaw64 if ctx.is_64 else TargetSwiftClassRaw32
            raw: RawSwiftClassT = self.runtime.read_struct(cls_struct, address)

        name = self.runtime.read_string(raw_data.name)
        cls = ObjCClass(raw, raw_data, name)
        class_methods = raw_data.flags & (1 << 0)  # why?
        if raw_data.base_methods:
            cls.methods = MethodIterator.get_instance(
                self.runtime,
                raw_data.base_methods,  # ptr
                cls,  # parent
                class_context=class_methods,
            )

        if raw_data.base_protocols:
            cls.protocols = ProtocolIterator.get_instance(
                self.runtime, raw_data.base_protocols, cls
            )

        if raw_data.base_properties:
            cls.properties = PropertyIterator.get_instance(
                self.runtime, raw_data.base_properties, cls
            )

        if raw.isa_storage and raw.isa_storage not in (raw._address, parent_address):
            cls.metaclass = self.load_at(raw.isa_storage, parent_address=raw._address)

        if raw.superclass and raw.superclass not in (raw._address, parent_address):
            cls.super_class = self.load_at(raw.superclass, parent_address=raw._address)

        if raw_data.ivars:
            cls.ivars = IVarIterator.get_instance(self.runtime, raw_data.ivars, cls)

        return cls


class CategoryIterator(ReflectionSectionIterator[ObjCCategory]):
    kind = "__objc_catlist"

    def __init__(self, __runtime: Runtime) -> None:
        # NOTE: we have to place this attribute definition before calling
        # super() as we want to skip type inspection
        is_64 = __runtime.is_64()
        self.struct = TargetCategoryRaw64 if is_64 else TargetCategoryRaw32
        super().__init__(__runtime, pointer_ty=cs.Int64ul if is_64 else cs.Int32ul)
        self.context.is_64 = is_64

    def _load_at(self, address: int, parent_address=0) -> ObjCCategory:
        raw: RawCategoryT = super()._load_at(address)
        name = self.runtime.read_string(raw.name)
        cat = ObjCCategory(raw, name)
        if raw.base_class:
            cat.base_class = self.runtime.classes.load_at(raw.base_class)

        if raw.class_methods:
            cat.class_methods = MethodIterator.get_instance(
                self.runtime, raw.class_methods, cat, class_context=True
            )

        if raw.instance_methods:
            cat.instance_methods = MethodIterator.get_instance(
                self.runtime, raw.instance_methods, cat, class_context=False
            )

        if raw.base_protocols:
            cat.protocols = ProtocolIterator.get_instance(
                self.runtime, raw.base_protocols, cat
            )

        if raw.instance_properties:
            cat.properties = PropertyIterator.get_instance(
                self.runtime, raw.instance_properties, cat
            )

        return cat


def has_objc_metadata(binary: lief.Binary) -> bool:
    for section in binary.sections:
        if section.name.startswith("__objc"):
            return True
    return False


class ObjCMetadata(Runtime):
    def __init__(self, __binary: lief.MachO.Binary) -> None:
        super().__init__(__binary)
        self._selectors = SelectorCache(
            # Create the cache based on the current word size
            self,
            pointer_ty=cs.Int64ul if self.is_64() else cs.Int32ul,
        )
        self._classes = ClassIterator(self)
        self._protocols = ProtocolIterator.global_instance(self)
        self._categories = CategoryIterator(self)

    @property
    def classes(self) -> ClassIterator:
        return self._classes

    @property
    def selectors(self) -> SelectorCache:
        return self._selectors

    @property
    def categories(self) -> CategoryIterator:
        return self._categories

    @property
    def protocols(self) -> ProtocolIterator:
        return self._protocols

    def get_import(self, selector: str) -> t.Optional[str]:
        # 1. Search imported symbols and return the framework path
        # if possible
        for symbol in self.binary.imported_symbols:
            # Filter relevant symbols
            if "_$_" in symbol.name:
                if symbol.name.split("_$_")[1] != selector:
                    continue

                # Found a symbol, check if it has a library bound to it
                if symbol.has_binding_info:
                    info = symbol.binding_info
                    # REVISIT: what if no library is present?
                    if info.has_library:
                        return info.library.name

    def is_local_import(self, selector: str) -> bool:
        # Search for local classes, protocols and categories
        for cache in (self.classes, self.categories, self.protocols):
            # NOTE: we will set the position here as the iterator may got used
            # before and does not point to index zero anymore
            cache.pos = cache.RESET
            for element in cache:
                if element.name == selector:
                    return True
        return False