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

import sys
import typing as t

from pygments.lexers.objective import SwiftLexer

import umbrella.swift as abi
from umbrella.dump import IDumper


def generic_param(index: int) -> str:
    return chr(ord("A") + (index % 26))


class SwiftDumper(IDumper):
    lexer = SwiftLexer
    use_demangler = True

    def dump_protocol(
        self, protocol: abi.TargetProtocolContextDescriptor, fp=None, depth=None
    ) -> None:
        """Dumps a protocol. (default to stdout)

        As of now, protocols are the easiest structure to dump as their fields
        (requirements) cannot be reversed, because the ABI does not define types
        or names to requirements of a protocol.

        When dumping a protocol, its generic signature (if any) will be reproduced.
        In addition, associated types will be printed as well. Detailed information
        about the protocol's requirements can be printed, if the dumper's depth is
        configured to include them.

        Example:
        >>> dumper.dump_protocol(protocol)
        public protocol Foo {
            // 1 Requirement
            // static var Getter
        }

        Available configuration:

        - ``MODULES``: includes the procotol's module
        - ``PROTO_REQUIREMENTS``: writes detailed information about requirements
        - ``PROTO_ASSOCTY``: writes associated type names

        :param protocol: the protocol to dump
        :type protocol: abi.TargetProtocolContextDescriptor
        :param fp: the output stream, defaults to None
        :type fp: io.IOBase, optional
        """
        self._start()
        self.depth = depth or 0

        name = self._get_context_name(protocol)
        sig_reqs = protocol.get_requirements_in_signature()
        requirements = protocol.get_requirements()
        if len(sig_reqs) == 0 and len(requirements) == 0:
            # Nothing important to print
            self <<= f"public protocol {name} {{}}"
        else:
            # Take a look at "_get_protocol_signature" to get more information about
            # how we restore the generic signature of a protocol.
            signature = self._get_protocol_signature(protocol)
            if signature:
                self <<= f"public protocol {name}: {signature} {{"
            else:
                self <<= f"public protocol {name} {{"

            self.indent += 2
            # associated types are easy to work with.
            for assocty in protocol.get_associated_type_names():
                self <<= f"associatedtype {assocty}"

            self <<= (
                # You should consider using PROTO_REQUIREMENTS to dump
                # additional information about each requirement
                f"// {len(requirements)} Requirement"
                + ("s" if len(requirements) != 1 else "")
            )
            for requirement in requirements:
                # Each requirement may be static, so we have to check that
                decl = "static var" if not requirement.flags.instance else "var"
                name = requirement.flags.kind.name
                self <<= f"// {decl} {name} "
                # Implementation may not be present
                impl = requirement.implementation.relative_offset
                if impl:
                    self << f"at {impl:#}"

            self.indent -= 2
            self <<= "}"
        # REVISIT: This line should be outsourced
        (fp or sys.stdout).write(self._finish())

    def dump_enum(self, enum: abi.TargetEnumContextDescriptor, fp=None, depth=None) -> None:
        """Dumps an enum structure. (default to stdout)

        Enums are defined to store empty and payload cases, as well as a generic
        signature (if an enum is annotated with a generic type). We are able to
        dump all fields with their mangled type names. Generics within an enum
        descriptor can't be reversed to 100 percent, so their generation will
        be skipped.

        Example:

        >>> dumper.dump_enum(enum)
        public enum test.Foo<A, B, C, D> {
            // Cases: 3, 1 empty
            case baz(param: Swift.String) # < resolved mangled name
            case foobar // $s\\x02_\\x91\\xff\\xff # < mangled name reference
            case bar
        }

        :param enum: the enum context descriptor
        :type enum: abi.TargetEnumContextDescriptor
        :param fp: the output stream, defaults to None
        :type fp: io.IOBase, optional
        """
        self._start()
        self.depth = depth or self.depth
        name = self._get_context_name(enum)
        self <<= f"public enum {name}"

        self._dump_generic_signature(enum)
        self << " {"
        fd = enum.get_fields()
        if fd is not None:
            self.indent += 2
            self <<= (
                # Small summary about what types of cases this enum stores
                f"// Cases: {enum.get_num_cases()}, {enum.num_empty_cases} empty"
            )
            fields = fd.get_fields()
            for field in fields:
                fmt = "case" if not field.is_indirect_case() else "indirect case"
                type_name = field.get_mangled_typename()
                name = field.get_field_name()
                self <<= f"{fmt} {name}"
                if type_name:
                    # Dump the type name within comments as the demangler is not
                    # stable yet.
                    type_ = self._demangle(type_name)
                    if type_[0] != "$":
                        self << (type_ if "(" in type_ else f"({type_})")
                    else:
                        self << f" // {type_}"

            self.indent -= 2
        self <<= "}"
        (fp or sys.stdout).write(self._finish())

    def dump_class(self, cls: abi.TargetClassContextDescriptor, fp=None, depth=None) -> None:
        self.dump(self._dump_class, cls, fp, self.indent, depth)

    def dump_struct(self, cls: abi.TargetClassContextDescriptor, fp=None, depth=None) -> None:
        self.dump(self._dump_struct, cls, fp, self.indent, depth)

    def _dump_class(self, cls: abi.TargetClassContextDescriptor) -> None:
        # TODO: implement me
        name = self._get_context_name(cls)
        self <<= f"public class {name}"

        has_signature = self._dump_generic_signature(cls)
        parent = cls.get_super_class_type()
        if parent:
            # Add super clas
            parent_name = self._demangle_name(parent)
            self << f": {parent_name}"
        elif not parent and not cls.super_class_type.is_null():
            self << ": ?"

        self << " {"
        if cls.is_reflectable():
            # The field descriptor MUST be non-null
            fd = cls.get_fields()
            if fd.num_fields > 0:
                self._dump_list(
                    fd.get_fields(),
                    self._dump_field,
                    "Properties/Fields",
                    self.indent + 2,
                )

        if has_signature:
            # NOTE: As generic classes are malformed in most cases, we don't
            # want to run into errors.
            self <<= " }"
            return

        if cls.has_vtable():
            # Dump all declared methods (private, public and static ones)
            self.indent += 2
            self <<= "// Methods"
            cls._fp.match_class_methods(cls, self._dump_function, cls_name=name)
            self.indent -= 2

        if cls.has_override_table():
            # overridden methods will be dumped with a reference to their
            # declaring class.
            methods = cls.get_override_methods()
            self._dump_list(
                methods,
                self._dump_override_function,
                "Overridden functions",
                self.indent + 2,
            )

        self <<= "}"

    def _dump_field(self, field: abi.FieldRecord) -> None:
        type_name = field.get_mangled_typename()
        name = field.get_field_name()
        self <<= "var " if field.is_var() else "let "
        if "$__lazy_storage_$" in name:
            name = name[17:]  # len(...)
            self << "lazy "

        self << name
        if type_name:
            # Dump the type name within comments as the demangler is not
            # stable yet.
            type_ = self._demangle(type_name)
            if type_[0] != "$":
                self << ": " << type_
            else:
                self << f" // {type_}"

    def _dump_function(
        self,
        method: abi.TargetMethodDescriptor,
        field: abi.FieldRecord = None,
        cls_name: str = None,
    ) -> None:
        # Because only functions declared as public will be visible within
        # a binary, we have to dump all other methods in a separate format.
        #   - /* <address> */ private [ static ] func '<stripped>' // <type>
        # In some special cases a method will be linked to a field using
        # ReflectionContext's match_class_methods function. The method name
        # will be built according to the given field's name.
        absolute_address = method._address + 4 + method.impl.relative_offset
        self <<= f"/* {absolute_address:#x} */ "

        fn = method._fp.get_function(method._address)  #: lief.Function
        self << ("" if fn is None else "public ")
        if not method.flags.instance:
            self << "static "

        if fn is None:
            if field is None:
                self << f"func <stripped> // {method.flags.get_kind_name()}"
            else:
                # Format the function according to the field's name
                short_name = (
                    # ModifyCoroutine => modify
                    method.flags.get_kind_name()
                    .lower()
                    .replace("coroutine", "")
                )
                field_name = field.get_field_name().removeprefix("$__lazy_storage_$")
                self << f"func {field_name}.{short_name} "
                # Re-structure the type name for this method:
                type_name = field.get_mangled_typename()
                if type_name:
                    # As implemented above, the type is not always demangled
                    type_ = self._demangle(type_name)
                    if type_[0] != "$":
                        self << f": {type_} // (stripped)"
                    else:
                        self << f"// {type_}, (stripped)"
                else:
                    self << "(stripped)"

            if method.flags.dynamic:
                self << " (dynamic)"
        else:
            # The function name and its parameters are described with a mangled
            # type name. We can use the swift executable to demangle the name.
            demangled_name = self._demangle(fn.name.encode())
            new_name = demangled_name.replace(cls_name, "").lstrip(".")
            self << "func " << new_name

    def _dump_override_function(
        self, method_od: abi.TargetMethodOverrideDescriptor
    ) -> None:
        # As this method override descriptor contains more than just its
        # implementation, we are able to dump more context information.
        absolute_address = method_od._address + 4 + method_od.impl.relative_offset
        method = method_od.method.get(method_od._address + 4)
        self <<= f"/* {absolute_address:#x} */ "
        if method is None:
            # This is very unlikely to happen, but it is necessary to check
            # here in order to prevent any issues
            self << "private override func <stripped>"
            return

        fn = method._fp.get_function(method._address)
        decl_cls = method_od.decl_class.ptr.get(method_od._address)
        decl_name = None
        if decl_cls:
            # We want to convert our context descriptor according to
            # its kind.
            decl_cls = decl_cls.cast()
            decl_name = self._get_context_name(decl_cls)

        if fn is None:
            # Same as above: no mangled type name
            if not method.flags.instance:
                self << "static "

            self << "override func <stripped> // " << method.flags.get_kind_name()
            if decl_name:
                self << " from " << decl_name
        else:
            self << "public "  # use public here as it gets exported
            if not method.flags.instance:
                self << "static "

            demangled_name = self._demangle(fn.name.encode())
            new_name = demangled_name.replace(decl_name or "", "").lstrip(".")
            self << "override func " << new_name
            if decl_name:
                self << " // from " << decl_name

    def _dump_struct(self, struct: abi.TargetStructContextDescriptor) -> None:
        name = self._get_context_name(struct)
        self <<= f"struct {name}"
        self._dump_generic_signature(struct)

        self << " {"
        if struct.is_reflectable():
            fd = struct.get_fields()
            self._dump_list(
                fd.get_fields(), self._dump_field, "Fields", self.indent + 2
            )
        self << "}"

    def _get_context_name(self, context) -> str:
        name = self._demangle_name(context.get_mangled_name())
        module = context.get_parent()
        while module:
            parent = module.cast()
            mangled_name = parent.get_mangled_name()
            if mangled_name:
                name = f"{self._demangle_name(mangled_name)}.{name}"
            module = module.get_parent()
        # Otherwise just return the mangled name
        return name

    def _demangle(self, name: bytes) -> str:
        if not name:
            return "<null>"

        return (
            repr(name)[2:-1] if not self.use_demangler else abi.demangler.demangle(name)
        )

    def _demangle_name(self, mangled_name: str) -> str:
        if any(map(lambda x: x.isdigit(), mangled_name)):
            return self._demangle(mangled_name.encode())

        if not all(map(lambda x: x.isprintable(), mangled_name)):
            return repr(mangled_name.encode())[2:-1]

        return mangled_name

    def _get_protocol_signature(self, protocol: abi.TargetProtocolContextDescriptor) -> str:
        # ---------------------- Protocol-Signature ----------------------
        # Each Swift protocol stores a so-called generic signature, which
        # defines base protocols and generic types. Note that all generic
        # requirements will be transformed into type parameters and will
        # receive a type with a special where clause.
        #   - protocol Bar: Foo, Equatable {...}
        # will become
        #   - protocol Bar: A, B where B: Foo {...}
        sig_reqs = protocol.get_requirements_in_signature()
        if len(sig_reqs) == 0:
            return ""

        args = []
        where_clauses = []
        for i, requirement in enumerate(sig_reqs):
            kind = requirement.get_kind()
            # Maybe fix this small issue: can we always expect 'x' as the
            # mangled typename?
            mangled_type_name = requirement.get_param()
            if not mangled_type_name or mangled_type_name == b"x":
                args.append(generic_param(i))
            else:
                args.append(self._demangle(mangled_type_name))

            if kind == abi.GenericRequirementKind.Protocol:
                # Direct protocol reference (most likely a hand-written protcol)
                ref_proto = requirement.get_protocol()
                if ref_proto:
                    where_clauses.append(f"{args[-1]}: {ref_proto.get_mangled_name()}")
            elif kind == abi.GenericRequirementKind.Layout:
                # ignore this block
                pass
            elif kind == abi.GenericRequirementKind.SameConformance:
                # ignote this one too
                pass
            else:
                # Default class types will be referenced by their mangled name
                type_name = requirement.get_mangled_typename()
                where = f"{args[-1]}: {self._demangle(type_name)}"
                where_clauses.append(where)

        # Last step: build protocol signature
        types = ", ".join(args)
        if len(where_clauses) == 0:
            return f"{types}"

        return f"{types} where {', '.join(where_clauses)}"

    def _dump_generic_signature(self, context) -> bool:
        signature = context.get_generic_signature()
        if signature is not None:
            # The only structure that appears to be the same across plattforms
            # is the array of GenericParamDescriptor. We only print type parameter
            # names here.
            params = [generic_param(i) for i in range(len(signature.params))]
            self << f"<{', '.join(params)}>"
            return True
