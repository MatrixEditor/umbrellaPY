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


# pointer type
PointerTy = t.TypeVar("PointerTy")
PointerT = t.Union[PointerTy, cs.Construct]

class PointerUnion(cs.Adapter, t.Generic[PointerTy]):
    value: int # the pointer value

    def __init__(self, subcon):
        # Default subcon will be int64
        super().__init__(subcon)

    def _decode(self, obj, context, path):
        # We have to create a new object here as it would result in
        # errors if we have only one instance
        ptr = type(self)(self.subcon)
        ptr.value = obj
        return ptr

    def _encode(self, obj, context, path):
        # just return the integer value
        return obj

    def get_pointer(self) -> int:
        # sanitize the pointer value
        return self.value & ~1

    def has_tag(self) -> bool:
        return bool(self.value & 1)

# 64-bit arch
PointerUnion64 = PointerUnion(cs.Int64ul)
# 32-bit arch
PointerUnion32 = PointerUnion(cs.Int32ul)

Pointer32 = cs.Int32ul

# 64-bit pointer
@cs.singleton
class Pointer64(cs.Adapter):
    def __init__(self):
        super().__init__(cs.Int64ul)

    def _decode(self, obj, context, path):
        # From Apple's source code:
        # "Strip TBI bits. We'll only use the top four bits at most so only
        # strip those. Does nothing on targets that don't have TBI."
        return obj & 0x7FFFFFFFFFFF

    def _encode(self, obj, context, path):
        return obj
