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

from pygments.lexers.objective import ObjectiveCppLexer

from umbrella.dump import IDumper
from umbrella.objc import (
    ObjCIVar,
    ObjCMethod,
    ObjCProperty,
    ObjCClass,
    ObjCCategory,
    ObjCProtocol,
    decoder,
)


class ObjCDumper(IDumper):
    """Implementation of an Objective-C class dumper.

    Lexing is done using the `ObjectiveCppLexer` of the pygments module. By default,
    comments will be inserted to annotate the current element section. This class
    implements dumping for the following objective-c structures:

    - :class:`ObjCClass`
    - :class:`ObjCCategory`
    - :class:`ObjCProtocol`

    These main types will be available by their corresponding dumping method. Each
    type can be dumped directly to an output stream. For instance,

    >>> dd = ObjCDumper()
    >>> dd.dump_class(objc_class)
    '''@interface FooViewController: AdvancedFooViewController
    // Instance Methods
    - (void)viewDidLoad // 0x100006fc4
    - (id)createSettingsForBar:(id) // 0x100007140
    @end'''

    Note that the default formatte won't use any coloring. To support colors on terminal
    output, simply set the formatter attribute:

    >>> dd = ObjCDumper(fmt_opts={"bg": "dark"}) # dark background colors
    >>> dd.formatter = TerminalFormatter         # imported from pygments

    There are implementations on basic objective-c types too. The following types can't
    be dumped directly:

    - :class:`ObjCIVar`
    - :class:`ObjCMethod`
    - :class:`ObjCProperty`

    To dump any of these types directly, you can use the `dump` method of this class:

    >>> method = ObjCMethod(...)
    >>> dd.dump(dd.dump_method, method)
    '- (id)createSettingsForBar:(id) // 0x100007140'
    """

    lexer = ObjectiveCppLexer

    def dump_ivar(self, ivar: ObjCIVar) -> None:
        # ----------------------- IVar Dump -----------------------
        # As Ivars are not that complicated, the structure of a dumped Ivar
        # is rather simple:
        #   - <ivar> := <type> <name>';'
        type_name = ivar.type_name
        name = ivar.name

        if not all((type_name, name)):
            # we are dealing with a remapped type (address is relocated -
            # NOT IMPLEMENTED)
            self <<= f"// {ivar.raw.offset:#x} <remapped>"
        else:
            type_desc = ivar.decode_type()
            self <<= f"{type_desc} "
            # NOTE: In some cases, especially when dumping basic ivars with a
            # protocol, the name may be hardcoded into the property's attributes.
            # Therefore, we have to check whether the name is already present in
            # the encoded type description.
            append_name = name not in type_name
            if append_name:
                self << name
            else:
                self << ("_$remapped_name" if not name[0].isprintable() else name)
            self << ";"

    def dump_method(self, method: ObjCMethod) -> None:
        # ----------------------- Method Dump -----------------------
        # Methods will be dumped with their signature and selector
        # combined.
        #   - <method> := [ '+' | '-' ] <signature>
        signature = method.decode_desc()
        if method.is_class_method:
            # Class methods will be annotated with a '+'
            self <<= "+ "
        else:
            self <<= "- "

        impl = method.raw.impl
        self << signature << f"; // {impl:#x}"

    def dump_property(self, prop: ObjCProperty) -> None:
        # ----------------------- Property Dump -----------------------
        # Properties will be treated like Ivars. Note that we don't assume
        # that there are remapped type names.
        #   - <property> := '@property' [ <attributes> ] <type> <name>
        desc = prop.decode_attributes()
        self <<= desc
        append_name = prop.name not in desc
        if append_name:
            # NOTE: In some cases, especially when dumping root properties,
            # the name may be hardcoded into the property's attributes. Therefore,
            # we have to check whether the name is already present in the encoded
            # type description.
            self << f" {prop.name}"
        self << ";"

    def dump_ivars(self, ivars: t.Iterable[ObjCIVar], comment: str = None):
        # Simple wrapper to dump a list of ivars
        self._dump_list(ivars, self.dump_ivar, comment, indent=self.indent + 2)

    def dump_methods(self, methods: t.Iterable[ObjCMethod], comment: str = None):
        # Simple wrapper to dump a list of methods
        self._dump_list(methods, self.dump_method, comment, indent=self.indent)

    def dump_properties(
        self, properties: t.Iterable[ObjCProperty], comment: str = None
    ):
        # Simple wrapper to dump a list of properties
        self._dump_list(properties, self.dump_property, comment, indent=self.indent)

    def dump_class(self, cls: ObjCClass, fp=None) -> None:
        # ----------------------- Class Dump -----------------------
        # Dumping a class is somewhat more comlicated, but can be broken
        # down into pieces. As classes may contain a metaclass (a class
        # that stores all 'static'/class methods, properties and ivars),
        # these attributes have to be dumped as well.
        self._start()
        name = decoder.objc_demangle_name(cls.name)
        super_cls = "NSObject"
        if cls.super_class:
            # REVISIT: the superclass can't be a protocol right?
            super_cls = decoder.objc_demangle_name(cls.super_class.name)

        self <<= f"@interface {name}: {super_cls} "
        if cls.protocols:
            # REVISIT: these names have to be demangled
            protocols = ", ".join(map(lambda x: x.name, cls.protocols))
            self << f"<{protocols}> "

        has_metaclass = bool(cls.metaclass)
        metaclass = cls.metaclass

        if cls.ivars or (has_metaclass and metaclass.ivars):
            self << "{"  # ivars will be placed into a block

        if cls.ivars:
            self.dump_ivars(cls.ivars, "Instance variables")

        if has_metaclass and metaclass.ivars:
            self.dump_ivars(cls.ivars, "Class variables")

        if cls.ivars or (has_metaclass and metaclass.ivars):
            self << "}\n"

        if cls.properties:
            self.dump_properties(cls.properties, "Instance Properties")

        if has_metaclass and metaclass.properties:
            self.dump_properties(metaclass.properties, "Class Properties")

        if cls.methods:
            self.dump_methods(cls.methods, "Instance Methods")

        if has_metaclass and metaclass.methods:
            self.dump_methods(metaclass.methods, "Class Methods")

        self << "@end"
        # Default output is stdout
        (fp or sys.stdout).write(self._finish())

    def dump_protocol(self, protocol: ObjCProtocol, fp=None) -> None:
        # ----------------------- Protocol Dump -----------------------
        # Protocol dumps will store a detailed overview of stored methods
        # and properties. Especially methods will be devided into class and
        # instance methods, which then will be devided into optional and
        # required methods.
        self._start()
        name = decoder.objc_demangle_name(protocol.name)

        self <<= f"@protocol {name} "
        if protocol.protocols:
            # Protocol conformances
            protocols = ", ".join(map(lambda x: x.name, protocol.protocols))
            self << f"<{protocols}> "

        if protocol.instance_properties:
            self.dump_properties(protocol.instance_properties, "Instance properties")

        if protocol.optional_class_methods or protocol.optional_instance_methods:
            self <<= "@optional"

        if protocol.optional_instance_methods:
            self.dump_methods(
                protocol.optional_instance_methods, "Optional instance methods"
            )

        if protocol.optional_class_methods:
            self.dump_methods(protocol.optional_class_methods, "Optional class methods")

        if protocol.required_class_methods or protocol.required_instance_methods:
            self <<= "@required"

        if protocol.required_instance_methods:
            self.dump_methods(
                protocol.required_instance_methods, "Required instance methods"
            )

        if protocol.required_class_methods:
            self.dump_methods(protocol.required_class_methods, "Required class methods")

        self << "@end"
        (fp or sys.stdout).write(self._finish())

    def dump_category(self, category: ObjCCategory, fp=None) -> None:
        # ----------------------- Category Dump -----------------------
        # Categories and extensions will be dumped using this method as
        # tarq doesn't differ between categories and extensions. Methods
        # will be devided into class and instance methods.
        self._start()
        name = category.name

        self <<= f"@interface {name} "
        if not category.is_extension():
            # base name only if this category is a 'real' category
            base_name = decoder.objc_demangle_name(category.base_class.name)
            self << f"({base_name}) "
        else:
            self << "() "

        if category.protocols:
            protocols = ", ".join(map(lambda x: x.name, category.protocols))
            self <<= f"({protocols})"

        if category.properties:
            self.dump_properties(category.properties, "Properties")

        if category.instance_methods:
            self.dump_methods(category.instance_methods, "Instance Methods")

        if category.class_methods:
            self.dump_methods(category.class_methods, "Class Methods")

        self << "@end"
        (fp or sys.stdout).write(self._finish())

