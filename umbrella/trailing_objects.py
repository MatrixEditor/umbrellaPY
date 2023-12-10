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
import inspect

import construct as cs
import dataclasses as dc
import construct_dataclasses as csd

from umbrella.runtime import sizeof

# Construct or dataclass type
T = t.TypeVar("T", bound=cs.Construct)

# simple solution to accept Token[...] values within a method call
Token = t.Type
TrailingTys = t.TypeVarTuple("TrailingTys")

class TrailingObjects(t.Generic[*TrailingTys]):
    """Python implementation of TrailingObjects found in the Swift ABI.

    This class uses typing to inspect annotated types and create trailer
    information based on them. You can think of "trailing objects" when
    using this class, for instance:

    >>> @dataclass
    ... class Foo:
    ...     a: int = csfield(Int32ul)
    ...

    Now, we want to have additional trailing objects based on runtime
    conditions at the end of each ``Foo`` object. We now create another
    class that stores our new "trailing" information:

    >>> @dataclass
    ... class Bar:
    ...     x: int = csfield(Int32ul)
    ...

    By annotating the previously defined class *Foo* with this class, one
    or multiple *Bar* objects will be placed as trailing objects at the
    end of each *Foo* instance virtually.

    >>> @dataclass
    ... class Foo(TrailingObjects[Bar]):
    ...     a: int = csfield(Int32ul)
    ...     # in order to get the amount of trailing Bar objects, a function
    ...     # must be defined, otherwise 1 is used
    ...     def _num_bar(self) -> int:
    ...         return self.a

    Each trailing object can be retrieved by calling ``getTrailingObject(s)``.
    The return value will be a tuple or single value based on the provided count.

    >>> foo = Foo(a=2) # retrieve Foo instance
    >>> foo.getTrailingObjects(Bar)
    (Bar(x=1), Bar(x=2))
    >>> foo.getTrailingObject(Bar)
    Bar(x=1)

    The amount of trailing objects will be computed per type. Each type may have
    a method mapped to it. The naming convention of each method is as follows:

    >>> nameof(Foo)
    '_num_foo'
    >>> nameof(FooBar)
    '_num_foo_bar'
    """

    # The internal representation of this structure that stores all
    # trailing structs
    # __trailing__: t.Tuple[*TrailingTys]

    # A list of length values that must be added to the base address of
    # this object
    # __sizes__: t.List[int]

    def __new__(cls, **kwargs) -> t.Self:
        super_new = super().__new__
        obj = super_new(cls)
        super(TrailingObjects, obj).__init__()
        assert dc.is_dataclass(cls), "Only dataclasses are supported!"

        # First, setup additional attributes that are fixed:
        fields = list(map(lambda f: f.name, dc.fields(obj)))
        for name, value in kwargs.items():
            if name not in fields:
                raise AttributeError(f"Invalid attr '{name}' - not found")

            setattr(obj, name, value)

        # In order to retrieve our trailing object types, we have to
        # inspect the type arguments of our class
        bases = list(obj.__orig_bases__)
        # If there are more than one base class, ensure we use the
        # right one
        base = None
        for base_type in bases:
            # The target type is generic, so we have to use the __origin__
            # attribute
            origin = t.get_origin(base_type)
            if origin and origin == TrailingObjects:
                base = base_type
                break
            # See TrailingGenericContextObjects for more details
            if getattr(origin, "__generic_root__", False):
                base = base_type
                break

        if base is None:
            raise ValueError("Could not determine base class!")

        trailing = []
        # Get all trailing objects and validate we have
        #   1. no duplicate types
        #   2. only instances of the DataclassStruct class
        for argument in t.get_args(base):
            if not isinstance(argument, csd.DataclassStruct):  # 1
                # BUT: we can create structs if the arguments are
                # dataclasses
                if dc.is_dataclass(argument):
                    argument = csd.DataclassStruct(argument)
                else:
                    raise TypeError(
                        f"Only constructs are approved as parameters - got {argument}"
                    )

            if argument in trailing:  # 2
                raise ValueError(f"Duplicate trailing type found: {argument}")

            trailing.append(argument)

        # Create a new internal reference
        setattr(obj, "__trailing__", trailing)
        setattr(obj, "__sizes__", []) # Intended for future use
        setattr(obj, "__struct__", csd.DataclassStruct(obj.__class__))
        setattr(obj, "__cached__", [None] * len(trailing))
        return obj

    def _index_of(self, token: Token[T]) -> int:
        base_ty = token
        # Try to search for the given token. the default return
        # value shoule be -1 to mitigate possible exceptions
        for i, ty in enumerate(self.__trailing__):
            if ty == base_ty:
                return i

            if isinstance(ty, csd.DataclassStruct):
                # Case: our dataclass has been turned into a DataclassStruct
                # using csd.DataclassStruct. We can use the model field to
                # identify the used type.
                if ty.model == base_ty:
                    return i

        return -1

    def _get_address(self, until: int) -> int:
        if until == -1:
            until = len(self.__trailing__)

        # REVISIT: maybe hardcode the sizeof value somehow
        struct = self.__struct__
        base_address = self._address + sizeof(struct)

        for i in range(until):
            ty_struct: csd.DataclassStruct = self.__trailing__[i]
            count = self._count(ty_struct)

            # Using Construct.sizeof(...) to calculate size
            length = count * sizeof(ty_struct)
            base_address += length

        return base_address

    def _count(self, ty_struct) -> int:
        # Try to resolve possible dynamic-sized elements by calling
        # an internal function with the following signature:
        #   - _num_<class-name>(self, fp) -> int
        if not isinstance(ty_struct, csd.DataclassStruct):
            name = self._map_name(ty_struct.__class__.__name__)
        else:
            name = self._map_name(ty_struct.model.__name__)
        fn_name = f"_num_{name}"
        if not hasattr(self, fn_name):
            # We automatically assume 1 as default count
            count = 1
        else:
            # The attribute may also be a fixed integer
            fn = getattr(self, fn_name)
            if isinstance(fn, int):
                count = fn

            elif isinstance(fn, t.Callable):
                # REVISIT: maybe use try: ... except: ... here
                # Check the number of arguments first
                args, *_ = inspect.getargs(fn.__code__)
                assert len(args) <= 2, f"Invalid arg-count on funciton: '{fn}'"
                if len(args) == 1: # only 'self' argument
                    count = fn()
                elif len(args) == 2: # self + fp argument
                    count = fn(self._fp)

            else:
                raise TypeError(f"Invalid count type - {type(fn)}")
        return count

    def _map_name(self, name: str) -> str:
        result = ""
        for ch in name:
            result += ch if ch.islower() else f"_{ch}"
        return result.removeprefix("_").lower()

    def getTrailingObject(self, token: Token[T]) -> t.Optional[T]:
        """Retrieves a single trailing object based on the provided token.

        :param token: the token annotated with the trailing type
        :type token: Token[T]
        :return: the parsed trailing object
        :rtype: t.Optional[T]
        """
        value = self.getTrailingObjects(token)
        if value is None:
            return None
        # Extract single value and discard all other values
        rvalue, *_ = value
        return rvalue

    def getTrailingObjects(self, token: Token[T]) -> t.Optional[t.Tuple[T]]:
        """Retrieves one or multiple trailing objects.

        If a trailing object is optional, the count should be set to zero, which
        in result leads to a null value returned by this method.

        :param token: the token annotated with the trailing type
        :type token: Token[T]
        :raises TypeError: if the provided type is not present in the
                           defined trailing objects
        :return: the parsed objects as tuple (always as tuple)
        :rtype: t.Optional[t.Tuple[T]]
        """
        # We shall not support any invalid type references. DataclassStructs
        # will be detected automatically.
        index = self._index_of(token)
        if index < 0:
            raise TypeError(f"Could not find trailing object of type '{token}'")

        struct = self.__trailing__[index]
        cached = self.__cached__[index]
        if cached is not None:
            if isinstance(cached, t.Iterable):
                return tuple(cached)
            return (cached,)

        address = self._get_address(index)

        count = self._count(struct)
        if count == 1:
            value = self._fp.read_struct(struct, address)
            self.__cached__[index] = value
            return (value,)
        elif count == 0:
            # Default return value for trailing objects that are
            # configured to be optional
            return None

        size = sizeof(struct)
        values = []
        for _ in range(count):
            # REVISIT: more read_struct calls, but we have the
            # struct's memoy address
            values.append(self._fp.read_struct(struct, address))
            address += size

        self.__cached__[index] = values
        return tuple(values)

    def sizeof(self, **contextkw) -> int:
        """Method that calculates the size of this struct"""
        end_address = self._get_address(-1)
        return end_address - self._address
