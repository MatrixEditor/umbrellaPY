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

__doc__ = """Generic (lazy) iterator classes."""

import abc
import typing as t

import construct as cs
from construct_dataclasses import DataclassStruct

from umbrella.runtime import Runtime

# All types in this file will be using this type var for an element type
E = t.TypeVar("E")


class CachingIterator(abc.ABC, t.Generic[E]):
    """Base class for all iterators that cache their parsed values.

    When iterating over elements, the following method order is applied:

    - ``__iter__`` to start the iteration
    - ``__next__`` to prepare the next element
    - ``_load`` performs the actual parsing of the next element

    Note that this iterator also supports list-like access. You can reference
    each element with its index position. The method ordering is as follows

    - ``__getitem__`` gets called on item access
    - (*) ``__next__`` if the iterator has to parse additional values
    - (*) ``_load`` if additional elements has to be parsed

    Examples:

    >>> iterator = ...
    >>> # Get all elements of an iterator (parsed ones)
    >>> elements = iterator.elements
    >>> # Get all elements (including elements that have to be parsed)
    >>> elements = iterator.all()
    >>> # Get an element by its index
    >>> element = iterator[4]
    >>> # Use slicing to get mulitple elements
    >>> elements = iterator[2:5]
    """

    #: Additional field to mark the reset value for this iterator
    RESET = -1

    def __init__(self) -> None:
        super().__init__()
        # The current position. Note the -1 here
        self.__pos = self.RESET
        # cached elements
        self.__elements = []

    @property
    def pos(self) -> int:
        """The current position as an integer value

        :return: the current position (may be -1)
        :rtype: int
        """
        return self.__pos

    @pos.setter
    def pos(self, value: int) -> None:
        """Sets the current position

        :param value: the new position
        :type value: int
        """
        self.__pos = value

    @property
    def elements(self) -> t.List[E]:
        """Returns all cached elements of this iterator.

        Note that this property will return all elements that have been
        parsed so far. Use ``all()`` for a list of all elements including
        the ones to be parsed.

        :return: all stored elements
        :rtype: t.List[E]
        """
        return self.__elements

    def all(self) -> t.List[E]:
        """Returns a list of all elements including the ones to be parsed.

        this call is equivalent to ``list(...)``.

        :return: a list of all elements.
        :rtype: t.List[E]
        """
        try:
            return list(self)
        except StopIteration:
            # As this iterator may be at the end already,
            # we should return all cached element directly.
            return self.__elements

    @abc.abstractmethod
    def _load(self, pos: int) -> E:
        """Parses an element at the current index position.

        :param pos: the index position
        :type pos: int
        :return: the parsed element
        :rtype: E
        """
        pass

    def __len__(self) -> int:
        """Returns the length of this iterator (if present)

        .. hint::
            You can raise an ``IndexError`` if your iterator does not have a
            fixed size.

        :raises NotImplementedError: by default, raises an error
        :return: the size of this iterator
        :rtype: int
        """
        raise NotImplementedError(f"len() not applicable for {type(self)}")

    def __iter__(self) -> t.Generator[E, t.Any, None]:
        while True:
            try:
                # The returned element won't be null
                yield next(self)
            except StopIteration:
                break

    def __next__(self) -> E:
        # Stops this iterator if it is are positioned at the end
        try:
            if self.__pos >= len(self) - 1:
                raise StopIteration
        except IndexError:
            # This error assumes that an iterator is defined to be
            # generic and will raise StopIterator accordingly.
            pass

        _pos = self.pos + 1  # because we start from 0
        element = self._load(_pos)
        self.elements.append(element)

        self.pos = self.pos + 1
        return element

    def __getitem__(self, key: t.Union[int, slice]) -> t.Union[t.Tuple[E], E]:
        if isinstance(key, slice):
            # Assign start, end and step sized based on the given slice
            # NOTE: negative step size is supported as well
            start, end, step = (
                key.start or 0,
                key.stop or len(self) - 1,
                key.step or 1,
            )
        else:
            # Otherwise all sizes are the same
            start = end = key
            step = 1

        if start < 0 or end > len(self):
            raise IndexError(f"index {key} out of bounds!")

        if start == end:
            if self.pos >= end:
                # NOTE: a tuple is returned for simplicity
                return self.__elements[end]

        else:
            if start < self.pos and self.pos > end:
                return self.__elements[start:end:step]

        try:
            while self.pos < end:
                # We have to iterate/parse all remaining elements until
                # the position matched the given end
                next(self)
        except StopIteration:
            pass

        return (
            self.__elements[end]
            if start == end
            else tuple(self.__elements[start:end:step])
        )


class LazyIterator(CachingIterator[E]):
    """
    Partial implementation of a :class:`CachingIterator` to integrate a
    runtime object.

    This class uses an internal context to store any additional variables
    used by the iterator. See :class:`ReflectionSectionIterator` for more
    details on possible usage.

    In addition, this class introduces a *length* field, which is used to
    determine the length of this iterator. Subclasses must specify the
    legth attribute with a string assigned to reference a context variable.

    >>> class Foo(LazyIterator):
    ...     length = "foo_length"

    Here, the referenced length variable ``"foo_length"`` must be set in
    the internal context within the ``_preload_context`` method.
    """

    # A field used by sub-classes to reference a context variable
    length: str

    def __init__(self, runtime: Runtime, **kwds) -> None:
        super().__init__()
        self._runtime = runtime
        self._context = cs.Container()
        # All values must be loaded before we ca actually operate
        # on the iterator instance
        self._preload_context(**kwds)

    def _preload_context(self, **kwds) -> None:
        """Prepares the internal context."""

    @property
    def runtime(self) -> Runtime:
        """Returns the associated runtime

        :return: the runtime object
        :rtype: Runtime
        """
        return self._runtime

    @property
    def context(self) -> cs.Container:
        """Returns the internal context

        :return: the internal context with all relevant values
        :rtype: Container
        """
        return self._context

    def __len__(self) -> int:
        # Small verification no the length field
        assert hasattr(self, "length"), "Missing 'length' field!"

        # This access will fail if we specify an invalid length reference
        value = self.context[self.length]
        if isinstance(value, int):
            return value

        # It is also possible to reference lists or dictionaries
        return len(value)


class ReflectionSectionIterator(LazyIterator[E]):
    """Base iterator class used to iterate over structs in a reflection section.

    Using python's type inspection only the section's name has to be provided.
    Everything else is configured automatically. For example,

    >>> class Foo: ... # assume this class is a dataclass
    >>> class FooIterator(ReflectionSectionIterator[Foo]):
    ...     kind = "__foo_section"
    ...
    >>> it = FooIterator(runtime)
    >>> foo = it[0] # get next element

    The method ordering is a little bit different compared to the initial iterator
    class. When iterating, the following methods will be executed:

    1. ``_load`` to parse the current element
    2. ``_address_of`` retrieves the current load address
    3. ``load_at`` looks for cached elements first before parsing
    4. (*) ``_load_at`` parses the next element if not already cached
    """

    # Used to determine the annotated generic class
    __root__ = "ReflectionSectionIterator"

    length = "addresses"  # length field
    kind: str  # section name
    struct: t.Type[E]  # the struct's type

    def __init__(
        self, runtime: Runtime, pointer_ty: cs.Construct = None, **kwds
    ) -> None:
        self._pointer_type = pointer_ty or cs.Int64ul
        super().__init__(runtime)

        if getattr(self, "struct", None):
            # Skip if struct has already been set
            return

        # The struct's tyoe can be retrieved by inspecting the type
        # arguments
        bases = list(self.__orig_bases__)
        # If there are more than one base class, ensure we use the
        # right one
        base = None
        for base_type in bases:
            origin = t.get_origin(base_type)
            if origin and origin.__name__ == self.__root__:
                base = base_type
                break

        assert (
            base is not None
        ), "Could not locate base class of 'ReflectionSectionIterator'"

        # Create the struct instance directly
        (struct,) = t.get_args(base)
        self.struct = DataclassStruct(struct)

    def _preload_context(self, **kwds) -> None:
        # Loads a pointer section named by 'kind'
        assert self.kind is not None, "Invalid kind for a reflection section"
        ptrs = self.runtime.read_ptr_section(self.kind, struct=self._pointer_type)
        self.context.addresses = list(ptrs.keys())
        self.context.ptrs = list(ptrs.values())
        # Additional attribute to map addresses to parsed elements
        self.context.ptr2type = {}

    def _load_at(self, address: int, parent_address=0) -> E:
        # Just uses the runtime to parse the struct
        return self.runtime.read_struct(self.struct, address, fix=True)

    def _address_of(self, pos: int) -> int:
        # NOTE: this function uses assumes absolute pointers by default
        return self.context.ptrs[pos]

    def _load(self, pos: int) -> E:
        # Implementation of the load function (simplified)
        address = self._address_of(pos)
        return self._load_at(address)

    def load_at(self, vaddress: int, parent_address=0) -> t.Optional[E]:
        """Loads a new struct at the given virtual address.

        :param vaddress: the virtual memory address
        :type vaddress: int
        :return: the parsed struct or nothing on an invalid address
        :rtype: t.Optional[E]
        """
        ptr2type = self.context.ptr2type

        obj = ptr2type.get(vaddress)
        if obj is None:
            obj = self._load_at(vaddress, parent_address=parent_address)
            ptr2type[vaddress] = obj

        return obj
