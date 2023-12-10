# Copyright (c) 2023 MatrixEditor
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import annotations

# Field descriptions taken from:
# ---------------------------------------------------------------------
# Specification: JSR-396 Java SE 21
# Version: 21
# Status: Final Release
# Release: September 2023
#
# Copyright © 1997, 2023, Oracle America, Inc.
# All rights reserved.
# ---------------------------------------------------------------------

import typing as t
import dataclasses as dc

import construct as cs
import construct_dataclasses as csd


from umbrella.runtime import uint16_t, uint32_t, uint8_t, get_context_value
from umbrella.java import (
    Flags,
    FieldAccessFlags,
    MethodAccessFlags,
    ClassAccessFlags,
    ParameterAccessFlags,
    ModuleAccessFlags,
    ModuleRequiresAccessFlags,
    ModuleExportsAccessFlags,
    ModuleOpensAccessFlags,
    AccessFlags
)


def _get_info_name(context) -> t.Optional[str]:
    constant_pool = get_context_value(context, "constant_pool")
    info = constant_pool.pool[context.name_index - 1]
    if info.data is not None:
        return getattr(info.data, "value")


class AttributeInfoAdapter(cs.Construct):
    def __init__(self, length):
        super().__init__()
        self.length = length
        self.subcon = None

    def get_subcon(self) -> cs.Construct:
        if not self.subcon:
            self.subcon = cs.Array(self.length, csd.DataclassStruct(AttributeInfo))
        return self.subcon

    def _parse(self, stream, context, path):
        subcon = self.get_subcon()
        return subcon._parse(stream, context, path)

    def _build(self, obj, stream, context, path):
        subcon = self.get_subcon()
        return subcon._build(obj, stream, context, path)


@csd.dataclass_struct
class Exceptions:
    #: The number_of_exceptions item's value specifies the number of entries
    #: in the exception_index_table.
    num_exceptions: uint16_t = csd.csfield(cs.Int16ub)

    #: Each value within the exception_index_table array must be a valid index
    #: within the constant_pool table. The constant_pool entry referenced by
    #: each item in the table must be a CnstantUTF8 structure representing a
    #: class type that this method is declared to throw.
    exception_index_table: t.List[uint16_t] = csd.csfield(
        cs.Array(cs.this.num_exceptions, cs.Int16ub)
    )


@csd.dataclass_struct
class InnerClass:
    #: The inner_class_info_index item's value must be a valid index within
    #: the constant_pool table. The entry in the constant_pool at that index
    #: must be a CONSTANT_Class_info structure representing class C. The
    #: remaining items within the classes array entry provide information about
    #: C.
    inner_class_info_index: uint16_t = csd.csfield(cs.Int16ub)

    #: If C is not a member of a class or an interface (i.e., if C is a
    #: top-level class or interface, or a local class, or an anonymous class), the
    #: value of the outer_class_info_index item must be zero.
    outer_class_info_index: uint16_t = csd.csfield(cs.Int16ub)

    #: If C is an anonymous class, the value of the inner_name_index item must
    #: be zero.
    inner_name_index: uint16_t = csd.csfield(cs.Int16ub)

    #: The value of the inner_class_access_flags item is a bitmask of flags
    #: used to specify access permissions and properties of class or interface C,
    #: as declared in the source code from which this class file was compiled.
    #: This information is used by a compiler to reconstruct the original details
    #: when the source code is unavailable.
    inner_class_access_flags: AccessFlags = csd.csfield(Flags(ClassAccessFlags))


@csd.dataclass_struct
class InnerClasses:
    #: The number_of_classes item's value indicates the number of entries in
    #: the classes array.
    num_inner_classes: uint16_t = csd.csfield(cs.Int16ub)

    #: Each ConstantClass entry in the constant_pool table, representing a
    #: class or interface C that is not a package member, must have
    #: precisely one corresponding entry in the classes array.
    classes: t.List[uint16_t] = csd.csfield(
        cs.Array(cs.this.num_inner_classes, InnerClass.parser)
    )


@csd.dataclass_struct
class CodeException:
    #: The values of the two items, start_pc and end_pc, indicate the ranges
    #: in the code array where the exception handler is active. The value of
    #: start_pc must be a valid index pointing to the opcode of an instruction
    #: within the code array. The value of end_pc must either be a valid index
    #: pointing to the opcode of an instruction within the code array or must
    #: equal code_length, which is the length of the code array. It's important
    #: to note that start_pc must be less than end_pc.
    start_pc: uint16_t = csd.csfield(cs.Int16ub)
    end_pc: uint16_t = csd.csfield(cs.Int16ub)

    #: The value of the handler_pc item indicates the beginning of the
    #: exception handler. This value must be a valid index pointing to the opcode
    #: of an instruction within the code array.
    handler_pc: uint16_t = csd.csfield(cs.Int16ub)

    #: If the value of the catch_type item is nonzero, it must be a valid
    #: index within the constant_pool table. The entry in the constant_pool at
    #: that index must be a CONSTANT_Class_info structure representing a class
    #: of exceptions that this exception handler is intended to catch. The
    #: exception handler will only be invoked if the thrown exception is an
    #: instance of the specified class or one of its subclasses.
    catch_type: uint16_t = csd.csfield(cs.Int16ub)


@csd.dataclass_struct
class Code:
    #: The max_stack item's value specifies the maximum depth of the operand
    #: stack for this method at any point during its execution.
    max_stack: uint16_t = csd.csfield(cs.Int16ub)

    #: The max_locals item's value indicates the number of local variables in
    #: the local variable array allocated upon invocation of this method,
    #: including those used for passing parameters to the method during its
    #: invocation.
    max_locals: uint16_t = csd.csfield(cs.Int16ub)

    #: The code_length item's value denotes the number of bytes in the code
    #: array for this method. It must be greater than zero, and the code array
    #: must not be empty.
    code_length: uint16_t = csd.csfield(cs.Int32ub)

    #: The code array contains the actual bytes of Java Virtual Machine code
    #: that implement the method.
    bytecode: uint16_t = csd.csfield(cs.Array(cs.this.code_length, cs.Int8ub))

    #: The exception_table_length item's value specifies the number of entries
    #: in the exception_table table.
    exception_table_length: uint16_t = csd.csfield(cs.Int16ub)

    #: Each entry in the exception_table array describes an exception handler
    #: in the code array, and their order in the exception_table array is
    #: significant.
    exception_table: t.List[CodeException] = csd.csfield(
        cs.Array(cs.this.exception_table_length, CodeException.parser)
    )

    #: The attributes_count item's value indicates the number of attributes
    #: associated with the Code attribute.
    num_attributes: uint16_t = csd.csfield(cs.Int16ub)

    #: Each entry in the attributes table must be an attribute structure. A
    #: Code attribute can have any number of optional attributes associated with
    #: it.
    attributes: t.List[AttributeInfo] = csd.csfield(
        AttributeInfoAdapter(cs.this.num_attributes)
    )


@csd.dataclass_struct
class AttributeRef:
    #: The constant_pool entry at that index provides the constant value represented
    #: by this attribute.
    index: uint16_t = csd.csfield(cs.Int16ub)


# NOTE: we have to declare classes here as they are used within the
# kAttributeTypes constants.
class ConstantValue(AttributeRef):
    pass


class Signature(AttributeRef):
    pass


class SourceFile(AttributeRef):
    pass


@csd.dataclass_struct
class EnclosingMethod:
    #: The class_index item's value must be a valid index within the
    #: constant_pool table. The entry in the constant_pool at that index must
    #: be a CONSTANT_Class_info structure representing the innermost
    #: class that encompasses the declaration of the current class.
    class_index: uint16_t = csd.csfield(cs.Int16ub)

    #: If the current class is not directly enclosed by a method or constructor,
    #: then the value of the method_index item must be zero
    name_index: uint16_t = csd.csfield(cs.Int16ub)


@csd.dataclass_struct
class LineNumber:
    #: The start_pc item's value must indicate the index within the code array
    #: where the code for a new line in the original source file starts.
    start_pc: uint16_t = csd.csfield(cs.Int16ub)

    #: The line_number item's value must specify the corresponding line number
    #: in the original source file.
    line_number: uint16_t = csd.csfield(cs.Int16ub)


@csd.dataclass_struct
class LineNumberTable:
    #: The line_number_table_length item's value indicates the number of
    #: entries in the line_number_table array.
    line_number_table_length: uint16_t = csd.csfield(cs.Int16ub)

    #: Each entry in the line_number_table array signifies that the line
    #: number in the original source file changes at a specific point in the code
    #: array.
    line_number_table: t.List[LineNumber] = csd.csfield(
        cs.Array(cs.this.line_number_table_length, LineNumber.parser)
    )


@csd.dataclass_struct
class LocalVariable:
    #: The specified local variable must have a value within the code array
    #: indices falling within the range [start_pc, start_pc + length), where
    #: start_pc is inclusive, and start_pc + length is exclusive.
    start_pc: uint16_t = csd.csfield(cs.Int16ub)
    length: uint16_t = csd.csfield(cs.Int16ub)

    #: The name_index item's value must be a valid index within the
    #: constant_pool table. The entry in the constant_pool at that index must
    #: contain a CONSTANT_Utf8_info structure representing a valid unqualified
    #: name that identifies a local variable.
    name_index: uint16_t = csd.csfield(cs.Int16ub)

    #: The descriptor_index item's value must be a valid index within the
    #: constant_pool table. The entry in the constant_pool at that index must
    #: contain a CONSTANT_Utf8_info structure representing a field descriptor
    #: encoding the type of a local variable in the source program.
    descriptor_index: uint16_t = csd.csfield(cs.Int16ub)

    #: The specified local variable must be located at the index within the
    #: local variable array of the current frame.
    index: uint16_t = csd.csfield(cs.Int16ub)


@csd.dataclass_struct
class LocalVariableTable:
    #: The local_variable_table_length item's value indicates the number of
    #: entries in the local_variable_table array.
    local_variable_table_length: uint16_t = csd.csfield(cs.Int16ub)

    #: Each entry in the local_variable_table array denotes a range of code
    #: array offsets where a local variable holds a value. It also specifies the
    #: index within the local variable array of the current frame where that local
    #: variable can be found.
    local_variable_table: t.List[LocalVariable] = csd.csfield(
        cs.Array(cs.this.local_variable_table_length, LocalVariable.parser)
    )


@csd.dataclass_struct
class LocalVariableType:
    #: The specified local variable must hold a value within the code array
    #: indices ranging from [start_pc, start_pc + length), where start_pc is
    #: inclusive, and start_pc + length is exclusive.
    start_pc: uint16_t = csd.csfield(cs.Int16ub)
    length: uint16_t = csd.csfield(cs.Int16ub)

    #: The value of the name_index item must be a valid index within the
    #: constant_pool table. The entry in the constant_pool at that index must
    #: contain a CONSTANT_Utf8_info structure representing a valid unqualified
    #: name identifying a local variable.
    name_index: uint16_t = csd.csfield(cs.Int16ub)

    #: The value of the signature_index item must be a valid index within the
    #: constant_pool table. The entry in the constant_pool at that index must
    #: contain a CONSTANT_Utf8_info structure representing a field type
    #: signature encoding the type of a local variable in the source program.
    signature_index: uint16_t = csd.csfield(cs.Int16ub)

    #: The specified local variable must be located at the index within the
    #: local variable array of the current frame.
    index: uint16_t = csd.csfield(cs.Int16ub)


@csd.dataclass_struct
class LocalVariableTypeTable:
    #: The value of the local_variable_type_table_length item indicates the
    #: number of entries in the local_variable_type_table array.
    local_variable_type_table_length: uint16_t = csd.csfield(cs.Int16ub)

    #: Each entry in the local_variable_type_table array designates a range of
    #: code array offsets where a local variable holds a value. It also specifies
    #: the index within the local variable array of the current frame where that
    #: local variable can be found.
    local_variable_type_table: t.List[LocalVariable] = csd.csfield(
        cs.Array(cs.this.local_variable_type_table_length, LocalVariable.parser)
    )


kElementValueTypeClass = "c"
kElementValueTypeAnnotation = "@"
kElementValueTypeEnum = "e"
kElementValueTypeString = "s"
kElementValueTypeArray = "["


@csd.dataclass_struct
class EnumConstValue:
    #: The type_name_index item's value must be a valid index within the
    #: constant_pool table. The entry in the constant_pool at that index must
    #: be a ConstantUTF8 structure representing a valid field descriptor
    #: that indicates the internal form of the binary name of the type of the enum
    #: constant represented by this element_value structure.
    type_name_index: uint16_t = csd.csfield(cs.Int16ub)

    #: The const_name_index item's value must be a valid index within the
    #: constant_pool table. The entry in the constant_pool at that index must
    #: be a CONSTANT_Utf8_info structure representing the simple name of the
    #: enum constant represented by this element_value structure.
    const_name_index: uint16_t = csd.csfield(cs.Int16ub)


class ElementValueAdapter(cs.Construct):
    def _parse(self, stream, context, path):
        tag = chr(get_context_value(context, "tag"))
        cls = cs.Int16ub
        # NOTE: lazyness necessary
        if tag == kElementValueTypeClass:
            cls = AttributeRef.parser
        elif tag == kElementValueTypeAnnotation:
            cls = Annotation.parser
        elif tag == kElementValueTypeEnum:
            cls = EnumConstValue.parser
        elif tag == kElementValueTypeArray:
            cls = ArrayValue.parser

        return cls._parse(stream, context, path)

    def _build(self, obj, stream, context, path):
        if isinstance(obj, int):
            return cs.Int16ub._build(obj, stream, context, path)
        return obj.parser._build(obj, stream, context, path)


@csd.dataclass_struct
class ElementValue:
    #: The tag item specifies the type of this annotation element-value pair.
    #:
    #: The letters B, C, D, F, I, J, S, and Z denote primitive types. These
    #: letters are interpreted as if they were field descriptors.
    tag: uint8_t = csd.csfield(cs.Int8ub)

    #: The value item represents the value of this annotation element.
    value: t.Union[int, Annotation, EnumConstValue, AttributeRef] = csd.csfield(
        ElementValueAdapter()
    )


@csd.dataclass_struct
class ArrayValue:
    #: The num_values item's value specifies the number of elements in the
    #: array-typed value represented by this element_value structure.
    num_values: uint16_t = csd.csfield(cs.Int16ub)

    #: Each entry in the values table provides the value of an element within
    #: the array-typed value represented by this element_value structure.
    values: t.List[ElementValue] = csd.csfield(
        cs.Array(cs.this.num_values, ElementValue.parser)
    )


@csd.dataclass_struct
class ElementValuePair:
    #: The element_name_index item's value must be a valid index within the
    #: constant_pool table. The entry in the constant_pool at that index must
    #: be a ConstantUTF8 structure representing a valid field descriptor
    #: that identifies the name of the annotation type element represented by this
    #: element_value_pairs entry.
    element_name_index: uint16_t = csd.csfield(cs.Int16ub)

    #: The value item represents the value of the element-value pair depicted
    #: by this element_value_pairs entry.
    value: ElementValue = csd.csfield(ElementValue.parser)


@csd.dataclass_struct
class Annotation:
    #: The type_index item's value must be a valid index within the
    #: constant_pool table. The entry in the constant_pool at that index must
    #: be a ConstantUTF8 structure representing a field descriptor that
    #: represents the annotation type corresponding to the annotation represented
    #: by this annotation structure.
    type_index: uint16_t = csd.csfield(cs.Int16ub)

    #: The num_element_value_pairs item's value specifies the number of
    #: element-value pairs in the annotation represented by this annotation
    #: structure.
    num_element_value_pairs: uint16_t = csd.csfield(cs.Int16ub)

    #: Each entry in the element_value_pairs table represents a single
    #: element-value pair within the annotation represented by this annotation
    #: structure.
    element_value_pairs: t.List[ElementValuePair] = csd.csfield(
        cs.Array(cs.this.num_element_value_pairs, ElementValuePair.parser)
    )


@csd.dataclass_struct
class RuntimeAnnotations:
    #: The num_annotations item's value specifies the number of
    #: run-time-(in)visible annotations represented by the structure.
    num_annotations: uint16_t = csd.csfield(cs.Int16ub)

    #: Each entry in the annotations table represents a single
    #: run-time-(in)visible annotation on a program element.
    annotations: t.List[Annotation] = csd.csfield(
        cs.Array(cs.this.num_annonations, Annotation.parser)
    )


class RuntimeVisibleAnnotations(RuntimeAnnotations):
    pass


class RuntimeInvisibleAnnotations(RuntimeAnnotations):
    pass


@csd.dataclass_struct
class ParameterAnnotation:
    #: The num_annotations item's value indicates the count of
    #: run-time-visible annotations on the parameter that corresponds to the
    #: sequence number of this parameter_annotations element.
    num_annotations: uint16_t = csd.csfield(cs.Int16ub)

    #: Each entry in the annotations table represents a single
    #: run-time-visible annotation on the parameter corresponding to the sequence
    #: number of this parameter_annotations element.
    annotations: t.List[Annotation] = csd.csfield(
        cs.Array(cs.this.num_annonations, Annotation.parser)
    )


@csd.dataclass_struct
class RuntimeParameterAnnotations:
    #: The num_parameters item specifies the number of parameters in the
    #: method represented by the method_info structure in which this annotation
    #: occurs. (This information is duplicated in the method descriptor.)
    num_parameters: uint16_t = csd.csfield(cs.Int16ub)

    #: Each entry in the parameter_annotations table aggregates all
    #: run-time-(in)visible annotations on a single parameter. The order of values in
    #: the table corresponds to the order of parameters in the method descriptor.
    parameter_annotations: t.List[ParameterAnnotation] = csd.csfield(
        cs.Array(cs.this.num_parameters, ParameterAnnotation.parser)
    )


class RuntimeVisibleParameterAnnotations(RuntimeParameterAnnotations):
    pass


class RuntimeInvisibleParameterAnnotations(RuntimeParameterAnnotations):
    pass


@csd.dataclass_struct
class AnnotationDefault:
    #: The default_value item represents the default value of the annotation
    #: type element whose default value is represented by this AnnotationDefault
    #: attribute.
    default_value: ElementValue = csd.csfield(ElementValue.parser)


@csd.dataclass_struct
class BootstrapMethod:
    #: The bootstrap_method_ref item's value must be a valid index within the
    #: constant_pool table. The entry in the constant_pool at that index must
    #: be a CONSTANT_MethodHandle_info structure.
    bootstrap_method_ref: uint16_t = csd.csfield(cs.Int16ub)

    #: The num_bootstrap_arguments item indicates the number of items in the
    #: bootstrap_arguments array.
    num_bootstrap_arguments: uint16_t = csd.csfield(cs.Int16ub)

    #: Each entry in the bootstrap_arguments array must be a valid index
    #: within the constant_pool table.
    bootstrap_arguments: t.List[uint16_t] = csd.csfield(
        cs.Array(cs.this.num_bootstrap_arguments, cs.Int16ub)
    )


@csd.dataclass_struct
class BootstrapMethods:
    #: The num_bootstrap_methods item determines the number of bootstrap
    #: method specifiers in the bootstrap_methods array.
    num_bootstrap_methods: uint16_t = csd.csfield(cs.Int16ub)

    #: Each entry in the bootstrap_methods array contains an index pointing to
    #: a CONSTANT_MethodHandle_info structure that specifies a bootstrap method,
    #: along with a sequence (possibly empty) of indexes to static arguments for
    #: the bootstrap method.
    bootstrap_methods: t.List[BootstrapMethod] = csd.csfield(
        cs.Array(cs.this.num_bootstrap_methods, BootstrapMethod.parser)
    )


@csd.dataclass_struct
class MethodParameter:
    #: The name_index item's value must either be zero or a valid index within
    #: the constant_pool table.
    name_index: uint16_t = csd.csfield(cs.Int16ub)

    #: The access flags of the parameter
    access_flags: AccessFlags = csd.csfield(Flags(ParameterAccessFlags))


@csd.dataclass_struct
class MethodParameters:
    #: The parameters_count item's value indicates the count of parameter
    #: descriptors in the method descriptor referenced by the descriptor_index
    #: of the attribute's enclosing method_info structure.
    parameters_count: uint16_t = csd.csfield(cs.Int16ub)
    parameters: t.List[MethodParameter] = csd.csfield(
        cs.Array(cs.this.parameters_count, MethodParameter.parser)
    )


@csd.dataclass_struct
class Module:
    """Java Module Attribute"""

    #: The module_name_index item's value must be a valid index within the
    #: constant_pool table. The entry in the constant_pool at that index must
    #: be a CONSTANT_Module_info structure representing the current
    #: module.
    module_name_index: uint16_t = csd.csfield(cs.Int16ub)

    #: The module_flags item's value
    module_flags: AccessFlags = csd.csfield(Flags(ModuleAccessFlags))

    #: The module_version_index item's value must be either zero or a valid
    #: index within the constant_pool table. If the item's value is zero, then
    #: no version information about the current module is provided. If the item's
    #: value is nonzero, then the entry in the constant_pool at that index must
    #: be a CONSTANT_Utf8_info structure representing the version of the current
    #: module.
    module_version_index: uint16_t = csd.csfield(cs.Int16ub)

    @csd.dataclass_struct
    class Requires:
        #: The requires_index item's value must be a valid index within the
        #: constant_pool table. The entry in the constant_pool at that index
        #: must be a CONSTANT_Module_info structure denoting a module upon which
        #: the current module depends.
        requires_index: uint16_t = csd.csfield(cs.Int16ub)
        requires_flags: AccessFlags = csd.csfield(
            Flags(ModuleRequiresAccessFlags)
        )

        #: The requires_version_index item's value must be either zero or a
        #: valid index within the constant_pool table. If the item's value is
        #: zero, then no version information about the dependency is provided. If
        #: the item's value is nonzero, then the entry in the constant_pool at
        #: that index must be a CONSTANT_Utf8_info structure representing the
        #: version of the module specified by requires_index.
        requires_version_index: uint16_t = csd.csfield(cs.Int16ub)

    #: The requires_count item indicates the number of entries in the
    #: requires table.
    requires_count: uint16_t = csd.csfield(cs.Int16ub)

    #: Each entry in the requires table specifies a dependency of the current
    #: module.
    requires: t.List[Module.Requires] = csd.csfield(
        cs.Array(cs.this.requires_count, Requires.parser)
    )


    @csd.dataclass_struct
    class Exports:
        #: The exports_index item's value must be a valid index within the
        #: constant_pool table. The entry at that index in the constant_pool
        #: must be a CONSTANT_Package_info structure representing a
        #: package exported by the current module.
        exports_index: uint16_t = csd.csfield(cs.Int16ub)

        #: The exports_flags field's value
        exports_flags: AccessFlags = csd.csfield(
            Flags(ModuleExportsAccessFlags)
        )

        #: The exports_to_count indicates the count of entries in the
        #: exports_to_index table.
        exports_to_count: uint16_t = csd.csfield(cs.Int16ub)

        #: The value of each entry in the exports_to_index table must be a
        #: valid index within the constant_pool table. The entry at that index
        #: in the constant_pool must be a CONSTANT_Module_info structure
        #: designating a module whose code can access the types and members in
        #: this exported package.
        exports_to_index: t.List[uint16_t] = csd.csfield(
            cs.Array(cs.this.exports_to_count, cs.Int16ub)
        )


    #: The exports_count item indicates the count of entries in the exports
    #: table.
    exports_count: uint16_t = csd.csfield(cs.Int16ub)

    #: Each entry in the exports table specifies a package exported by the
    #: current module, enabling public and protected types in the package and
    #: their public and protected members to be accessed from outside the current
    #: module, potentially from a restricted set of "friend" modules.
    exports: t.List[Module.Exports] = csd.csfield(
        cs.Array(cs.this.exports_count, Exports.parser)
    )

    @csd.dataclass_struct
    class Opens:
        #: The opens_index item's value must be a valid index within the
        #: constant_pool table. The entry at that index in the constant_pool
        #: must be a CONSTANT_Package_info structure representing a package
        #: opened by the current module.
        opens_index: uint16_t = csd.csfield(cs.Int16ub)

        #: The opens_flags field's value
        opens_flags: AccessFlags = csd.csfield(
            Flags(ModuleOpensAccessFlags)
        )

        #: The opens_to_count indicates the count of entries in the
        #: opens_to_index table.
        opens_to_count: uint16_t = csd.csfield(cs.Int16ub)

        #: The value of each entry in the opens_to_index table must be a valid
        #: index within the constant_pool table. The entry at that index in the
        #: constant_pool must be a CONSTANT_Module_info structure denoting a
        #: module whose code can access the types and members in this opened
        #: package.
        opens_to_index: t.List[uint16_t] = csd.csfield(
            cs.Array(cs.this.opens_to_count, cs.Int16ub)
        )

    #: The opens_count item indicates the count of entries in the opens
    #: table.
    opens_count: uint16_t = csd.csfield(cs.Int16ub)

    #: Each entry in the opens table specifies a package opened by the current
    #: module, granting access to all types in the package and all their members
    #: from outside the current module through the Java SE Platform's reflection
    #: libraries, potentially from a limited set of "friend" modules.
    opens: t.List[Module.Exports] = csd.csfield(
        cs.Array(cs.this.exports_count, Exports.parser)
    )

    #: The uses_count item signifies the count of entries in the uses_index
    #: table.
    uses_count: uint16_t = csd.csfield(cs.Int16ub)

    #: Each entry in the uses_index table must be a valid index within the
    #: constant_pool table. The entry at that index in the constant_pool must
    #: be a CONSTANT_Class_info structure representing a service interface that
    #: the current module may discover using java.util.ServiceLoader.
    uses: t.List[uint16_t] = csd.csfield(
        cs.Array(cs.this.uses_count, cs.Int16ub)
    )

    @csd.dataclass_struct
    class Provides:
        #: The provides_index item must be a valid index within the
        #: constant_pool table. The entry at that index in the constant_pool
        #: must be a CONSTANT_Class_info structure representing a service
        #: interface for which the current module provides a service
        #: implementation.
        provides_index: uint16_t = csd.csfield(cs.Int16ub)

        #: The provides_with_count indicates the count of entries in the
        #: provides_with_index table.
        provides_with_count: uint16_t = csd.csfield(cs.Int16ub)

        #: Each entry in the provides_with_index table must be a valid index
        #: within the constant_pool table. The entry at that index in the
        #: constant_pool must be a CONSTANT_Class_info structure representing
        #: a service implementation for the service interface specified by
        #: provides_index.
        provides_with_index: t.List[uint16_t] = csd.csfield(
            cs.Array(cs.this.opens_to_count, cs.Int16ub)
        )

    #: The provides_count item indicates the count of entries in the
    #: provides table.
    provides_count: uint16_t = csd.csfield(cs.Int16ub)

    #: Each entry in the provides table represents a service implementation
    #: for a specific service interface.
    provides: t.List[Module.Provides] = csd.csfield(
        cs.Array(cs.this.provides_count, Provides.parser)
    )


@csd.dataclass_struct
class ModulePackages:
    #: The package_count item's value indicates the count of entries in the
    #: package_index table.
    package_count: uint16_t = csd.csfield(cs.Int16ub)

    #: Each entry in the package_index table must be a valid index within the
    #: constant_pool table. The entry at that index in the constant_pool must
    #: be a CONSTANT_Package_info structure representing a package
    #: within the current module.
    package_index: t.List[uint16_t] = csd.csfield(
        cs.Array(cs.this.package_count, cs.Int16ub)
    )

class NestHost(AttributeRef): pass
class ModuleMainClass(AttributeRef): pass

@csd.dataclass_struct
class NestMembers:
    #: The number_of_classes item's value indicates the count of entries in
    #: the classes array.
    number_of_classes: uint16_t = csd.csfield(cs.Int16ub)

    #: Each value in the classes array must be a valid index within the
    #: constant_pool table. The entry at that index in the constant_pool must
    #: be a CONSTANT_Class_info structure representing a class or
    #: interface that is a member of the nest hosted by the current class or
    #: interface.
    classes: t.List[uint16_t] = csd.csfield(
        cs.Array(cs.this.number_of_classes, cs.Int16ub)
    )


class PermittedSubclasses(NestMembers): pass


@csd.dataclass_struct
class RecordComponentInfo:
    #: The name_index item's value must be a valid index within the
    #: constant_pool table. The entry at that index in the constant_pool must
    #: be a CONSTANT_Utf8_info structure representing a valid unqualified name
    #: denoting the record component.
    name_index: uint16_t = csd.csfield(cs.Int16ub)

    #: The descriptor_index item's value must be a valid index within the
    #: constant_pool table. The entry at that index in the constant_pool must
    #: be a CONSTANT_Utf8_info structure representing a field descriptor
    #: encoding the type of the record component.
    descriptor_index: uint16_t = csd.csfield(cs.Int16ub)

    #: The attributes_count item indicates the number of additional attributes
    #: for this record component.
    attributes_count: uint16_t = csd.csfield(cs.Int16ub)

    #: Each value in the attributes table must be an attribute_info
    #: structure.
    attributes: t.List[AttributeInfo] = csd.csfield(
        AttributeInfoAdapter(cs.this.num_attributes)
    )

@csd.dataclass_struct
class Record:
    #: The components_count item indicates the number of entries in the
    #: components table.
    components_count: uint16_t = csd.csfield(cs.Int16ub)

    #: Each entry in the components table specifies a record component of the
    #: current class, in the order that the record components were declared.
    components: t.List[RecordComponentInfo] = csd.csfield(
        cs.Array(cs.this.components_count, RecordComponentInfo.parser)
    )


kAttributeTypes = (
    AnnotationDefault,
    BootstrapMethods,
    Code,
    ConstantValue,
    Exceptions,
    InnerClasses,
    LineNumberTable,
    LocalVariableTable,
    LocalVariableTypeTable,
    Module,
    ModuleMainClass,
    ModulePackages,
    NestHost,
    NestMembers,
    PermittedSubclasses,
    Record,
    RuntimeInvisibleAnnotations,
    RuntimeInvisibleParameterAnnotations,
    RuntimeVisibleAnnotations,
    RuntimeVisibleParameterAnnotations,
    Signature,
    SourceFile,
)


@dc.dataclass
class AttributeInfo:
    #: For all attributes, the attribute_name_index must be a valid unsigned 16-bit
    #: index within the constant pool of the class. The entry in the constant pool at
    #: attribute_name_index must be a ConstantUTF8 structure representing
    #: the name of the attribute.
    name_index: uint16_t = csd.csfield(cs.Int16ub)
    name: str = csd.csfield(cs.Computed(_get_info_name))

    #: The attribute_length item's value indicates the length, in bytes, of the
    #: subsequent information. Note that this length measurement does not include
    #: the initial six bytes that contain the attribute_name_index and
    #: attribute_length items.
    attribute_length: uint32_t = csd.csfield(cs.Int32ub)
    info: t.Union[*kAttributeTypes, bytes] = csd.csfield(
        cs.Switch(
            cs.this.name,
            cases={x.__name__: x.parser for x in kAttributeTypes},
            default=cs.Bytes(cs.this.attribute_length),
        )
    )


@dc.dataclass
class FieldInfo:
    #: The access_flags item's value is a bitmask of flags used to specify
    #: access permissions and properties of this field.
    access_flags: AccessFlags = csd.csfield(Flags(FieldAccessFlags))

    #: The name_index item's value must be a valid index within the constant_pool
    #: table. The entry in the constant_pool at that index must be a ConstantUTF8
    #: structure representing a valid unqualified name denoting a field.
    name_index: uint16_t = csd.csfield(cs.Int16ub)

    #: The descriptor_index item's value must be a valid index within the
    #: constant_pool table. The entry in the constant_pool at that index must be a
    #: ConstantUTF8 structure representing a valid field descriptor.
    descriptor_index: uint16_t = csd.csfield(cs.Int16ub)

    #: The attributes_count item's value indicates the number of additional attributes
    #: associated with this field.
    num_attributes: uint16_t = csd.csfield(cs.Int16ub)

    #: Each entry in the attributes table must be an attribute structure. A field can
    #: have any number of attributes associated with it.
    attributes: t.List[AttributeInfo] = csd.subcsfield(
        AttributeInfo, cs.Array(cs.this.num_attributes, csd.to_struct(AttributeInfo))
    )


@dc.dataclass
class MethodInfo:
    #: The access_flags item's value is a bitmask of flags used to specify access
    #: permissions and properties of this method.
    access_flags: AccessFlags = csd.csfield(Flags(MethodAccessFlags))

    #: The name_index item's value must be a valid index within the constant_pool
    #: table. The entry in the constant_pool at that index must be a ConstantUTF8
    #: structure representing either one of the special method names init or clinit,
    #: or a valid unqualified name denoting a method.
    name_index: uint16_t = csd.csfield(cs.Int16ub)

    #: The descriptor_index item's value must be a valid index within the constant_pool
    #: table. The entry in the constant_pool at that index must be a ConstantUTF8 structure
    #: representing a valid method descriptor.
    descriptor_index: uint16_t = csd.csfield(cs.Int16ub)

    #: The attributes_count item's value indicates the number of additional attributes
    #: associated with this method.
    num_attributes: uint16_t = csd.csfield(cs.Int16ub)

    #: Each entry in the attributes table must be an attribute structure. A method can have
    #: any number of optional attributes associated with it.
    attributes: t.List[AttributeInfo] = csd.subcsfield(
        AttributeInfo, cs.Array(cs.this.num_attributes, csd.to_struct(AttributeInfo))
    )

