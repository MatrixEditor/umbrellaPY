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

__doc__ = """Base classes for inspecting static Objective-C runtime information."""

import abc
import typing as t
import dataclasses as dc

from construct import Container

# We rather import type definitions here as it makes the code more
# readable.
from umbrella.objc import (
    RawPropertyT,
    RawIVarT,
    RawMethodT,
    RawClassDataT,
    RawClassT,
    RawProtocolT,
    RawSwiftClassT,
    RawCategoryT,
    decoder,
)
from umbrella.runtime import sizeof
from umbrella.iterator import LazyIterator

# Element type of an iterator
E = t.TypeVar("E")

# The parent of a runtime object may be a class, category or protocol. Objects
# within a root context don't store any parent.
ParentT = t.Union["ObjCClass", "ObjCCategory", "ObjCProtocol", None]


class BoundListIterator(LazyIterator[E]):
    """Objective-C list iterator for properties, protocols, ivars and methods.

    Subclasses should always take the following instantiation parameters:

    - ``lst``: the list instance
    - ``struct``: the struct which is used to parse underlying data
    - ``parent``: (optional) the parent object

    Note that sub-classes must override the ``_base_address`` to calculate the
    starting address.

    Parsing is done by delegating to ``_load_list_element``, which takes the
    virtual memory address as well as the operating context. This method must
    not return any null value. Before actually parsing the list element, a
    virtual address has to be calculated - this is done in ``_get_address``.
    Subclasses may override this method to implement a custom algorithm to get
    the current virtual address.
    """

    # We define the length field here so subclasses don't have to do that
    # on their own.
    length = "count"

    def _preload_context(self, **kwds) -> None:
        # We assume that the parsed list structure is always present.
        lst = kwds["lst"]
        # Load all necessary values
        self.context.parent = kwds.get("parent")
        self.context.lst = lst
        self.context.struct = kwds["struct"]
        self.context.count = lst.count
        self.context.address = self._base_address(lst._address)

    @abc.abstractmethod
    def _base_address(self, __address: int) -> int:
        # Calculates the starting address of this list (base address + size
        # of list structure)
        pass

    def _get_address(self, pos: int) -> int:
        ctx = self.context
        struct = ctx.struct
        return ctx.address + (pos * sizeof(struct))

    def _load(self, pos: int) -> E:
        # 1. Calculate the current virtual address
        address = self._get_address(pos)
        # 2. Load the next list element
        return self._load_list_element(address, self.context)

    @abc.abstractmethod
    def _load_list_element(self, raw_address: int, context: Container) -> E:
        # Tries to parse the next list element and returns the created runtime
        # object.
        pass


@dc.dataclass(frozen=True)
class ObjCIVar:
    """
    The `Ivar <https://developer.apple.com/documentation/objectivec/ivar?language=objc>`_
    runtime type implementation. For more information about its raw structure, see
    :class:`TargetIVarRaw64` or :class:`TargetIVarRaw32`.

    .. note::
        Ivar objects will store their mangled/encoded name by default. It can be
        decoded using `decode_type()`.
    """

    raw: RawIVarT  #: parsed raw structure
    name: str  #: the name of this ivar
    type_name: str  #: the encoded type-name of this ivar
    parent: ParentT  #: the parent context

    def decode_type(self) -> str:
        """Decodes the type-name of this ivar using the ``objc.decoder``.

        :return: the decoded type name
        :rtype: str
        """
        type_desc = decoder.objc_typedesc(self.type_name)
        return decoder.objc_decode(type_desc)


@dc.dataclass(frozen=True)
class ObjCMethod:
    """
    The Method runtime type implementation. See :class:`TargetMethodRaw64` or
    :class:`TargetMethodRaw32` for detailed information about the internal structure
    of an objc-method.

    .. hint::
        You can simply generate a fully qualified signature of this method by using
        ``decode_desc()``. It will produce something like this:

        >>> method = ObjCMethod(name="someMethod", signature="B16@0:8", ...)
        >>> method.decode_desc()
        '(BOOL)someMethod'
    """

    raw: RawMethodT  #: parsed raw structure
    name: str  #: the method's name (selector string)
    signature: str  #: the method's signature (encoded)
    is_class_method: bool  #: whether this method is a class method
    is_small: bool  #: whether this method stores relative pointers

    def decode_desc(self) -> str:
        """Decodes the signature of this method.

        >>> method = ObjCMethod(name="foo:bar:", signature="q32@0:8@16q24", ...)
        >>> method.decode_desc()
        '(long long)foo:(id) bar:(long long)'

        :return: the *decoded* signature.
        :rtype: str
        """
        return decoder.objc_signature(self.name, self.signature)

    def get_impl(self) -> int:
        """Returns the address for the implementation of this method

        :return: the implementation address
        :rtype: int
        """
        if self.is_small:
            # decoding the relative pointer
            return self.raw._address + 8 + self.raw.impl
        return self.raw.impl


@dc.dataclass(frozen=True)
class ObjCProperty:
    """
    The Property [#f4]_ runtime type implementation. :class:`TargetPropertyRaw64` or
    :class:`TargetPropertyRaw32` provide more information about the raw structure.
    """

    raw: RawPropertyT  #: the parsed structure
    name: str  #: the property's name
    attributes: str  #: its attributes
    parent: ParentT  #: the parent context

    def decode_attributes(self) -> str:
        """Decodes this property into a fully representative string.

        Example:

        >>> prop = ObjCProperty(name="foo", attributes='T@"NSMutableSet",&,N,V_foo', ...)
        >>> prop.decode_attributes()
        '@property (retain, nonatomic) NSMutableSet foo'

        :return: the decoded attributes as string
        :rtype: str
        """
        type_desc = decoder.objc_typedesc(self.attributes)
        return decoder.objc_decode(type_desc)


@dc.dataclass
class ObjCProtocol:
    """Runtime type of an Objective-C protocol."""

    raw: RawProtocolT #: the parsed raw structure
    name: str #: the parsed protocol name
    parent: ParentT #: the parent context

    #: all conformed protocols
    protocols: t.Optional[BoundListIterator[ObjCProtocol]] = None
    #: a list of required instance methods
    required_instance_methods: t.Optional[BoundListIterator[ObjCMethod]] = None
    #: a list of required class methods
    required_class_methods: t.Optional[BoundListIterator[ObjCMethod]] = None
    #: a list of optional instance methods
    optional_instance_methods: t.Optional[BoundListIterator[ObjCMethod]] = None
    #: a list of optional class methods
    optional_class_methods: t.Optional[BoundListIterator[ObjCMethod]] = None
    #: a list of defined instance properties
    instance_properties: t.Optional[BoundListIterator[ObjCProperty]] = None


@dc.dataclass
class ObjCClass:
    """
    The Class [#f2]_ runtime type implementation. This class may also represent
    an encoded Swift class, but it won't store Swift type information. These should
    be retrieved via a :class`SwiftRuntime` instance.

    All list attributes with a size greater than one will be set as a :class:`BoundListIterator`
    and are therefore lazy within their usage.
    """

    #: parsed raw class struct
    raw: RawClassT
    #: parsed raw class data
    raw_data: RawClassDataT

    #: the name of this class
    name: str
    #: the super class (optional)
    super_class: t.Optional[ObjCClass] = None
    #: the class of which this one is an instance
    metaclass: t.Optional[ObjCClass] = None
    #: an iterator over all defined methods
    methods: t.Optional[BoundListIterator[ObjCMethod]] = None
    #: all defined instance variables
    ivars: t.Optional[BoundListIterator[ObjCIVar]] = None
    #: a list of all conformed protocols
    protocols: t.Optional[BoundListIterator[ObjCProtocol]] = None
    #: a list of instance properties
    properties: t.Optional[BoundListIterator[ObjCProperty]] = None


@dc.dataclass
class ObjCCategory:
    """
    The `Category <https://developer.apple.com/documentation/objectivec/category?language=objc>`_
    runtime type implementation. More information about the raw structures can be taken
    from :class:`TargetCategoryRaw64` and :class:`TargetCategoryRaw32`.

    .. note::
        Categories with no base class are extensions.
    """

    raw: RawCategoryT #: the parsed raw structure
    name: str #: the parsed category name

    #: optional base class
    base_class: t.Optional[ObjCClass] = None
    #: defined class methods
    class_methods: t.Optional[BoundListIterator[ObjCMethod]] = None
    #: defined instance methods
    instance_methods: t.Optional[BoundListIterator[ObjCMethod]] = None
    #: all conformed protocols
    protocols: t.Optional[BoundListIterator[ObjCProtocol]] = None
    #: all defined additional properties
    properties: t.Optional[BoundListIterator[ObjCProperty]] = None

    def is_extension(self) -> bool:
        """Returns whether this categoriy is an extension.

        :return: true, if this category has no base class.
        :rtype: bool
        """
        return self.raw.base_class == 0
