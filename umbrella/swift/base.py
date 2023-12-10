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

import enum
import typing as t

import construct as cs
import capstone

from umbrella.runtime import Runtime, sizeof, __x64__
from umbrella.iterator import ReflectionSectionIterator


class ReflectionSectionKind(enum.Enum):
    macho_fieldmd = "__swift5_fieldmd"
    macho_assocty = "__swift5_assocty"
    macho_builtin = "__swift5_builtin"
    macho_capture = "__swift5_capture"
    macho_typeref = "__swift5_typeref"
    macho_typemd = "__swift5_types"
    macho_reflstr = "__swift5_reflstr"
    macho_conform = "__swift5_proto"
    macho_protocs = "__swift5_protos"
    macho_acfuncs = "__swift5_acfuncs"
    macho_mpenum = "__swift5_mpenum"

    pe_fieldmd = ".sw5flmd"
    pe_assocty = ".sw5asty"
    pe_builtin = ".sw5bltn"
    pe_capture = ".sw5cptr"
    pe_typeref = ".sw5tyrf"
    pe_typemd = ".sw5tymd"
    pe_reflstr = ".sw5rfst"
    pe_conform = ".sw5prtc"
    pe_protocs = ".sw5prt"
    pe_acfuncs = ".sw5scfn"
    pe_mpenum = ".sw5mpen"

    elf_fieldmd = "swift5_fieldmd"
    elf_assocty = "swift5_assocty"
    elf_builtin = "swift5_builtin"
    elf_capture = "swift5_capture"
    elf_typeref = "swift5_typeref"
    elf_typemd = "swift5_types"
    elf_reflstr = "swift5_reflstr"
    elf_conform = "swift5_protocol_conformances"
    elf_protocs = "swift5_protocols"
    elf_acfuncs = "swift5_accessible_functions"
    elf_mpenum = "swift5_mpenum"


E = t.TypeVar("E")


class SwiftSectionIterator(ReflectionSectionIterator[E]):
    __root__ = "SwiftSectionIterator"

    def __init__(self, __runtime: Runtime, /, **kwds) -> None:
        super().__init__(__runtime, cs.Int32sl, **kwds)

    def _preload_context(self, **kwds) -> None:
        kind_fmt = self.runtime.get_binary_kind()
        # Dynamic way to handle different binaries
        self.kind = getattr(ReflectionSectionKind, f"{kind_fmt}_{self.kind}").value
        return super()._preload_context(**kwds)

    def _address_of(self, pos: int) -> int:
        # Calculate relative addresses
        offset = super()._address_of(pos)
        return self.context.addresses[pos] + offset


class DynamicSwiftSectionIterator(SwiftSectionIterator[E]):
    __root__ = "DynamicSwiftSectionIterator"

    def __len__(self) -> int:
        # Rather don't throw an error when this section doesn't exists
        if self.context.address == 0:
            return 0

        raise IndexError(f"{self.__class__.__name__} is dynamic-sized!")

    def _preload_context(self, **kwds) -> None:
        kind_fmt = self.runtime.get_binary_kind()
        # Dynamic way to handle different binaries
        self.kind = getattr(ReflectionSectionKind, f"{kind_fmt}_{self.kind}").value

        # Skip parsing of pointer section
        section = self.runtime.binary.get_section(self.kind)
        self.context.ptr2type = {}
        if section is not None:
            self.context.address = section.virtual_address
            self.context.max_address = section.virtual_address + section.size
        else:
            self.context.address = 0
            self.context.max_address = 0

    def _address_of(self, pos: int) -> int:
        address = self.context.address
        if address >= self.context.max_address:
            raise StopIteration

        return address

    def _current_size(self, obj: E) -> int:
        # Default implementation, just take the struct's size
        return sizeof(self.struct, fp=self.runtime)

    def _load_at(self, address: int) -> E:
        # Before we can return the current element, we have to move our
        # address pointer forwards
        obj = super()._load_at(address)
        self.context.address = address + self._current_size(obj)
        return obj


def resolve_metadata_from_code(code_address: int, runtime: Runtime):
    binary = runtime.binary
    arm64 = __x64__(binary)
    arch = capstone.CS_ARCH_ARM64 if arm64 else capstone.CS_ARCH_ARM

    count = 200
    md = capstone.Cs(arch, capstone.CS_MODE_LITTLE_ENDIAN)
    # By default, Capstone does not generate details for disassembled
    # instructions. If we want information such as implicit registers
    # read/written or semantic groups that this instruction belongs
    # to, we need to explicitly turn this option on.
    md.detail = True
    code = bytes(binary.get_content_from_virtual_address(code_address, count))
    instructions = list(md.disasm(code, code_address, count))
    for i in range(1, 20):
        ins_add: capstone.CsInsn = instructions[i]
        ins_adrp: capstone.CsInsn = instructions[i - 1]

        if (
            ins_add.id != capstone.arm64.ARM64_INS_ADD
            or ins_adrp.id != capstone.arm64.ARM64_INS_ADRP
        ):
            continue

        adrp_operands = ins_adrp.operands
        add_operands = ins_add.operands
        if len(add_operands) != 3 or len(adrp_operands) != 2:
            continue

        if (
            adrp_operands[0].type != capstone.arm64.ARM64_OP_REG
            or adrp_operands[1].type != capstone.arm64.ARM64_OP_IMM
        ):
            continue

        if (
            add_operands[0].type != capstone.arm64.ARM64_OP_REG
            or add_operands[2].type != capstone.arm64.ARM64_OP_IMM
        ):
            continue

        if add_operands[0].reg != adrp_operands[0].reg:
            continue

        return adrp_operands[1].imm + add_operands[2].imm
