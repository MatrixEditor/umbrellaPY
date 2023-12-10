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

__doc__ = """Demangler implementation for Objective-C type encoding"""

import enum
import io
import typing as t
import dataclasses as dc

# public:


@dc.dataclass
class ObjCTypeNode:
    """Class to store mangled type information.

    All mangled types will be converted into type nodes.
    """

    type: int = 0  # the internal objective-c type
    size: int = 0  # the size in bytes
    alignment: int = 0  # alignment in bytes
    stack_size: int = 0  # parsed stack size

    # Attributes will be used if a property has been parsed. Each
    # attribute conforms to a property attribute.
    attr: t.List[str] = dc.field(default_factory=list)

    name: t.Optional[str] = None  # the node's name
    parent: t.Optional[ObjCTypeNode] = None  # the parent node

    # All children will be stored in a separate list
    children: t.List[ObjCTypeNode] = dc.field(default_factory=list)


def objc_typedesc(__signature: str) -> ObjCTypeNode:
    """Creates a type description based on the given signature.

    >>> demangler.objc_typedesc("v16@0:8")
    ObjCTypeNode(..., children=[ObjCTypeNode(type=<ObjCType.VOID: 14>, stack_size=16, name="void",...)])

    This function works with plain type encodings as well as method and property
    encodings. It is recommended to NOT use any other functions to create a type
    description besides this one.

    :param __signature: the raw type encoding
    :type __signature: str
    :return: the root :class:`ObjCTypeNode`
    :rtype: ObjCTypeNode
    """

    root = ObjCTypeNode()  # create the root node with no type
    sstream = PeekableStringIO(__signature)
    while not _objc_type_is_eof(sstream):
        child = _objc_type_parse(sstream, root)
        root.children.append(child)
    return root


def objc_decode(__typedesc: ObjCTypeNode) -> str:
    """Decodes a type description.

    Simple example with a primitive type:

    >>> desc = demangler.objc_typedesc("B")
    >>> demangler.objc_decode(desc)
    'BOOL'

    Property encodings are supported as well:

    >>> desc = demangler.objc_typedesc('T@"NSMutableSet",&,N,V_foo')
    >>> demangler.objc_decode(desc)
    '@property (retain, nonatomic) NSMutableSet foo'

    :param __typedesc: the type description node
    :type __typedesc: ObjCTypeNode
    :return: the decoded type (or property string)
    :rtype: str
    """
    if __typedesc.type == 0:
        value = []
        for child in __typedesc.children:
            value.append(_objc_decode(child))

        return " ".join(value)

    return _objc_decode(__typedesc)


def objc_signature(__selector: str, __signature: str) -> str:
    """Generates a fully qualified method signature.

    Example:
    >>> demangler.objc_signature("foo:bar:", "q32@0:8@16q24")
    '(long long)foo:(id) bar:(long long)'

    :param __selector: the method's selector string
    :type __selector: str
    :param __signature: the encoded signature
    :type __signature: str
    :raises SyntaxError: if the signature is malformed
    :return: the qualified signature as a string
    :rtype: str
    """
    selector = __selector
    signature = __signature

    typedesc = objc_typedesc(signature)
    children = typedesc.children[1:]
    rtype = typedesc.children[0]

    # remove return type and other unused types first
    if len(children) == 0:
        return f"({objc_decode(rtype)}){selector}"

    if len(children) < 2:
        raise SyntaxError("Missing '_cmd' parameter")

    children = children[2:]
    # Sanitize labels and add anonymous parameters
    selector = selector.replace("::", ":_")
    labels = [x for x in selector.split(":") if x]
    if len(children) == 0:
        return f"({objc_decode(rtype)}){selector}"

    if len(labels) != len(children):
        # "Expected {len(children)} labels, got {len(labels)} for {signature}"
        values = " ".join([f"({x})" for x in map(_objc_decode, children)])
        return f"({objc_decode(rtype)}){selector} {values}"

    values = []
    for label, child in zip(labels, children):
        values.append(f"{label}:({objc_decode(child)})")
    return f"({objc_decode(rtype)}){' '.join(values)}"


def objc_demangle_name(__name: str, is_protocol=False) -> str:
    """Demangles an objective-c type name that uses swift encoding.

    :param __name: the mangled name
    :type __name: str
    :param is_protocol: whether the type is a protocol, defaults to False
    :type is_protocol: bool, optional
    :return: the demangled name or the provided name on error
    :rtype: str
    """
    name = __name
    if not name:
        return __name

    # Swift mangling prefix
    if not name.startswith(("_TtP", "_TtC")):
        return name

    # remove prefix
    name = name[4:]
    # Get module name
    prefix = None
    if name.startswith("Ss"):
        prefix = "Swift"
        name = name[2:]
    else:
        prefix = _scan_mangled_field(name)
        if not prefix:
            return __name
        name_len = len(str(len(prefix)))
        name = name[name_len + len(prefix) :]

    # Class or protocol name
    suffix = _scan_mangled_field(name)
    if not suffix:
        return __name

    if is_protocol:
        # Remainder must be '_'
        if name[-1] != "_":
            return __name

    return f"{prefix}.{suffix}"


# private:


class ObjCType(enum.IntEnum):
    CHAR = 1
    INT = 2
    SHORT = 3
    LONG = 4
    LONG_LONG = 5
    UNSIGNED_CHAR = 6
    UNSIGNED_INT = 7
    UNSIGNED_SHORT = 8
    UNSIGNED_LONG = 9
    UNSIGNED_LONG_LONG = 10
    FLOAT = 11
    DOUBLE = 12
    BOOL = 13
    VOID = 14
    STRING = 15
    OBJECT = 16
    CLASS = 17
    SEL = 18
    ARRAY = 19
    STRUCT = 20
    UNION = 21
    BIT_FIELD = 22
    POINTER = 23
    NXATOM = 24
    ATTRIBUTES = 25
    BLOCK = 26
    UNKNOWN = 64


class ObjCAttributeType(enum.IntEnum):
    GETTER = 27
    SETTER = 28
    READONLY = 29
    COPY = 30
    RETAIN = 31
    NONATOMIC = 32
    DYNAMIC = 33
    WEAK = 34


class PeekableStringIO(io.StringIO):
    def peek(self, __count=1) -> str | None:
        try:
            index = self.tell()
            return self.getvalue()[index : index + __count]
        except IndexError:
            return None


ATTRIBUTES = {
    "R": ("readonly", ObjCAttributeType.READONLY),
    "C": ("copy", ObjCAttributeType.COPY),
    "&": ("retain", ObjCAttributeType.RETAIN),
    "N": ("nonatomic", ObjCAttributeType.NONATOMIC),
    "D": ("@dynamic", ObjCAttributeType.DYNAMIC),
    "W": ("__weak", ObjCAttributeType.WEAK),
    # "P": "eligible for garbage collection"
}

SIMPLE_TYPES = {
    "v": ("void", 0, ObjCType.VOID),
    "C": ("unsigned char", 1, ObjCType.UNSIGNED_CHAR),
    "c": ("char", 1, ObjCType.CHAR),
    "i": ("int", 4, ObjCType.INT),
    "I": ("unsigned int", 4, ObjCType.UNSIGNED_INT),
    "s": ("short", 2, ObjCType.SHORT),
    "S": ("unsigned short", 2, ObjCType.UNSIGNED_SHORT),
    "l": ("long", 8, ObjCType.LONG),
    "L": ("unsigned long", 8, ObjCType.UNSIGNED_LONG),
    "q": ("long long", 16, ObjCType.LONG_LONG),
    "Q": ("unsigned long long", 16, ObjCType.UNSIGNED_LONG_LONG),
    "f": ("float", 4, ObjCType.FLOAT),
    "d": ("double", 8, ObjCType.DOUBLE),
    "B": ("BOOL", 1, ObjCType.BOOL),
    "*": ("char *", 8, ObjCType.STRING),
    "#": ("Class", 8, ObjCType.CLASS),
    ":": ("SEL", 8, ObjCType.SEL),
    "?": ("<unknown>", 0, ObjCType.UNKNOWN),
    "%": ("NXAtom", 0, ObjCType.NXATOM),
}

# also states as modifiers; '+' is missing
METHOD_TYPES = {
    "r": "const",
    "n": "in",
    "N": "inout",
    "o": "out",
    "O": "bycopy",
    "R": "byref",
    "V": "oneway",
    "A": "atomic",
    "j": "complex",
}


def _objc_type_is_eof(buf: PeekableStringIO) -> bool:
    return not bool(buf.peek())


def _objc_type_parse_number(buf: PeekableStringIO) -> int:
    value = ""
    while "0" <= buf.peek() <= "9":
        value += buf.read(1)
    return int(value or "0")


def _objc_type_parse(
    buf: PeekableStringIO, parent: t.Optional[ObjCTypeNode]
) -> ObjCTypeNode:
    node = ObjCTypeNode(parent=parent)
    tok = buf.read(1)
    while tok in METHOD_TYPES:
        node.attr.append(METHOD_TYPES[tok])
        tok = buf.read(1)

    if tok in SIMPLE_TYPES:
        name, size, type_ = SIMPLE_TYPES[tok]
        node.name = name
        node.type = type_
        node.alignment = node.size = size
    elif tok == "^":
        _objc_type_parse_pointer(buf, node)
    elif tok == "[":
        _objc_type_parse_array(buf, node)
    elif tok == "{":
        _objc_type_parse_struct_or_union(ObjCType.STRUCT, buf, node)
    elif tok == "(":
        _objc_type_parse_struct_or_union(ObjCType.UNION, buf, node)
    elif tok == "@":
        _objc_parse_object(buf, node)
    elif tok == "b":
        _objc_parse_bitfield(buf, node)
    elif tok == '"':
        # Special case: struct member definition with starting with a name
        name = buf.read(1)
        while buf.peek() != '"' and not _objc_type_is_eof(buf):
            name += buf.read(1)
        # Skip '"' at the end
        buf.read(1)
        node = _objc_type_parse(buf, parent)
        node.name = name
    elif tok == "T":
        # Special case: the whole string defines property attributes
        attributes = buf.read().split(",")
        node.type = ObjCType.ATTRIBUTES
        # Child 0 is always the typedesc
        node.children.append(_objc_type_parse(PeekableStringIO(attributes[0]), node))
        # the last child is the name of the backing instance variable
        node.name = attributes[-1]
        if node.name in ATTRIBUTES:
            attributes = attributes[1:]
            node.name = None
        else:
            attributes = attributes[1:-1]

        for attribute in attributes:
            attr_node = ObjCTypeNode(parent=node)
            if attribute in ATTRIBUTES:
                attr_node.name, attr_node.type = ATTRIBUTES[attribute]
            elif attribute in ("G"):
                attr_node.name = attribute[1:]
                attr_node.type = ObjCAttributeType.GETTER
            elif attribute in ("S"):
                attr_node.name = attribute[1:]
                attr_node.type = ObjCAttributeType.SETTER

            node.children.append(attr_node)

    node.stack_size = _objc_type_parse_number(buf)
    return node


def _objc_parse_bitfield(buf: PeekableStringIO, node: ObjCTypeNode):
    count = _objc_type_parse_number(buf)
    node.size = count
    node.alignment = count
    node.type = ObjCType.BIT_FIELD


def _objc_parse_object(buf: PeekableStringIO, node: ObjCTypeNode):
    tok = buf.peek()
    if tok == "?":
        # Skip blocks
        tok = buf.read(1)
        if buf.peek() == "<":
            # actual block definition, parse that and return
            _objc_parse_block(buf, node)
            return

    if tok == '"':
        buf.read(1)  # skip '"'
        # parse additional name
        node.name = buf.read(1)
        while buf.peek() != '"' and not _objc_type_is_eof(buf):
            node.name += buf.read(1)
            # Skip '"' at the end
        buf.read(1)
    else:
        node.name = "id"
    node.type = ObjCType.OBJECT
    node.size = 8
    node.alignment = 8


def _objc_parse_block(buf: PeekableStringIO, node: ObjCTypeNode):
    tok = buf.peek()
    if tok == "<":
        # Skip block start
        buf.read(1)

    block_return_type = _objc_type_parse(buf, node)
    node.children.append(block_return_type)

    block_self = _objc_type_parse(buf, node)
    node.children.append(block_self)

    while buf.peek() != ">":
        child = _objc_type_parse(buf, node)
        node.children.append(child)
        node.size += child.size

    buf.read(1)  # skip '>' at the end
    node.type = ObjCType.BLOCK
    node.alignment = 8


def _objc_type_parse_pointer(buf: PeekableStringIO, parent: ObjCTypeNode) -> None:
    child = _objc_type_parse(buf, parent)
    parent.children.append(child)
    parent.type = ObjCType.POINTER
    parent.size = 8
    parent.alignment = 8


def _objc_type_parse_array(buf: PeekableStringIO, parent: ObjCTypeNode) -> None:
    count = _objc_type_parse_number(buf)
    child = _objc_type_parse(buf, parent)

    parent.children.append(child)
    parent.type = ObjCType.ARRAY
    parent.size = count
    parent.alignment = child.alignment

    tok = buf.peek()
    if tok == "]":
        buf.read(1)


def _objc_type_parse_struct_or_union(
    type_: ObjCType, buf: PeekableStringIO, parent: ObjCTypeNode
) -> None:
    # Structs are represented as "{name=??}", the cursor has moved pass '{'
    # when this function is called.
    struct_name = ""
    parent.type = type_

    close_tok = "}" if type_ == ObjCType.STRUCT else ")"
    while not _objc_type_is_eof(buf):
        tok = buf.read(1)
        if tok == "=":
            break

        if tok == close_tok:
            parent.name = struct_name
            return
        struct_name += tok

    parent.name = struct_name
    while not _objc_type_is_eof(buf):
        tok = buf.peek()
        if tok == close_tok:
            buf.read(1)  # skip close token
            break

        child = _objc_type_parse(buf, parent)
        parent.children.append(child)
        parent.alignment = max(parent.alignment, child.alignment)
        if type_ == ObjCType.STRUCT:
            parent.size += child.size
        else:
            parent.size = max(parent.size, child.size)


def _objc_decode(node: ObjCTypeNode) -> str:
    desc = []
    if len(node.attr) > 0:
        desc += node.attr

    if (
        node.type in list(map(lambda x: SIMPLE_TYPES[x][2], SIMPLE_TYPES))
        or node.type == ObjCType.OBJECT
    ):
        # name of simple types are set by default
        desc.append(node.name)

    elif node.type == ObjCType.BIT_FIELD:
        desc.append(f"BitField<{node.size}>")

    elif node.type == ObjCType.POINTER:
        child_decoding = _objc_decode(node.children[0])
        desc.append(child_decoding + ("*" if child_decoding[-1] == "*" else " *"))

    elif node.type == ObjCType.ARRAY:
        child_decoding = _objc_decode(node.children[0])
        if node.size == 0:
            desc.append(f"{child_decoding}[]")
        else:  # FIXME: this results in swapped dimensions
            desc.append(f"{child_decoding}[{node.size}]")

    elif node.type == ObjCType.STRUCT:
        # TODO: maybe add option to expand structs and unions
        desc.append(f"struct {node.name}")

    elif node.type == ObjCType.UNION:
        desc.append(f"union {node.name}")

    elif node.type == ObjCType.ATTRIBUTES:
        # First child is type
        typespec = node.children[0]
        attributes = node.children[1:]
        attr_desc = []
        is_dynamic = False
        for attribute in attributes:
            if attribute.type == ObjCAttributeType.GETTER:
                attr_desc.append(f"getter={attribute.name}")
            elif attribute.type == ObjCAttributeType.SETTER:
                attr_desc.append(f"setter={attribute.name}")
            elif attribute.type == ObjCAttributeType.DYNAMIC:
                is_dynamic = True
            elif attribute.name:
                attr_desc.append(attribute.name)

        if is_dynamic:
            desc.append("@dynamic")

        if len(attr_desc) > 0:
            desc.append(f"@property ({', '.join(attr_desc)})")
        else:
            desc.append("@property")
        desc.append(_objc_decode(typespec))

        if node.name:
            desc.append(node.name.lstrip("V").lstrip("_"))

    elif node.type == ObjCType.BLOCK:
        # void (^id)(NSError, )
        rtype, _, *params = node.children
        desc.append(_objc_decode(rtype))
        param_desc = ", ".join(map(_objc_decode, params))
        desc.append(f"(^_)({param_desc})")
    else:
        desc.append("?")  # for now

    return " ".join(desc)


def _scan_mangled_field(__name: str) -> t.Optional[str]:
    name = __name
    if name[0] == "0":
        return None

    length = ""
    for ch in name:
        if not ch.isdigit():
            break
        length += ch
    try:
        name_len = int(length)
    except ValueError:
        return None

    return name[len(length) : len(length) + name_len]
