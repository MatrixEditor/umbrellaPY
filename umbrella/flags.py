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

__doc__ = """Generic flags and flag-related classes."""

import typing as t
import construct as cs

E = t.TypeVar("E")


def from_flags(cls: t.Iterable[E], flags: int, mask: int = ~0) -> E:
    """Retrieves an enum value from the given flag

    :param cls: the enum class
    :type cls: t.Iterable[E]
    :param flags: one or multiple flags
    :type flags: int
    :param mask: the mask to apply to the provided flags, defaults to ~0
    :type mask: int, optional
    :return: either the enum value or returns the original if no suitable
             representation has been found.
    :rtype: E | int
    """
    value = flags & mask
    for enum_value in cls:
        if enum_value.value == value:
            return enum_value

    return value

# REVISIT: Why not parsing the flag directly. It would result in one
# field less in a class definition.
class Flags(cs.Adapter):
    """An adapter to parse flag-sets.

    Parsing does nothing, because this adapter uses ``Computed`` to retrieve the
    flag value. It then creates a new instance of type *flags_ty* and returns it.

    :param flags_ty: the class operating in parsed flags
    :type flags_ty: type
    :param selector: the context selector, defaults to "flags_value"
    :type selector: str, optional
    """

    def __init__(self, flags_ty, selector: str = "flags_value"):
        super().__init__(cs.Computed(lambda ctx: ctx[selector]))
        self.flags_ty = flags_ty

    def _decode(self, obj, context, path):
        return self.flags_ty(obj)

    def _encode(self, obj, context, path):
        return obj.flags

class FlagSet:
    """Simple class to represent a set of flags within an integer value.

    >>> flags = FlagSet(0b00010000110001)
    >>> flags.get_flag(0) #            ^
    True
    >>> flags.get_field(4, 2) #   ^^
    3
    >>> flags.get_flag(10) # ^
    True

    :param __flags: the flags value
    :type __flags: int
    """

    def __init__(self, __flags: int) -> None:
        #: The stored flags as an integer
        self.flags = __flags

    def __repr__(self) -> str:
        # Use the current class name instead of FlagsRepr
        name = self.__class__.__name__

        # Filter out any special variables
        names = filter(lambda x: not x.startswith("_"), self.__dict__.keys())

        # representation: foo='bar', baz=3
        values = ", ".join(map(lambda x: f"{x}={repr(getattr(self, x))}", names))
        return f"<{name} {values}>"

    def low_mask_for(self, bit_width: int) -> int:
        return (1 << bit_width) -1

    def mask_for(self, first_bit: int, bit_width: int = 1) -> int:
        return self.low_mask_for(bit_width) << first_bit

    def get_flag(self, bit: int) -> bool:
        """Read a single-bit flag.

        :param bit: the bit position
        :type bit: int
        :return: the extracted bit
        :rtype: bool
        """
        return bool(self.flags & self.mask_for(bit))

    def get_field(self, first_bit: int, bit_width: int) -> int:
        """Read a multi-bit field.

        :param first_bit: the first bit position
        :type first_bit: int
        :param bit_width: the width in bits
        :type bit_width: int
        :return: the extracted field
        :rtype: int
        """
        return (self.flags >> first_bit) & self.low_mask_for(bit_width)

    def __eq__(self, __value: FlagSet) -> bool:
        return __value.flags == self.flags

    def __ne__(self, __value: FlagSet) -> bool:
        return __value.flags != self.flags