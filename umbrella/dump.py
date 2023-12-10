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

from pygments import highlight
from pygments.lexer import Lexer
from pygments.formatter import Formatter
from pygments.formatters.other import NullFormatter

from umbrella.runtime import sizeof, Virtual


class IDumper:
    """Base class for all language dumpers.

    Both, Swift and Objective-C will implement a dumper class that can be used
    to dump source code. You can pass additional formatter options as keyword
    arguments within the constructor of this class.

    * ``fmt_opts``: This dictionary will store additional formatter options
    * ``lex_opts``: To support lexer options, this dictionary can be set in the keyword arguments

    In order to provide a simple-to-use interface, this class implements special
    features:

    >>> d = IDumper()
    >>> d._start()          # start a dumping process
    >>> d <<= "Hello World" # create a new line
    >>> d << "!"            # append to the current line
    >>> d._finish()
    'Hello World!'
    """

    #: lexer type to use
    lexer: t.Type[Lexer]

    #: The formatter type to use
    formatter: t.Type[Formatter] = NullFormatter

    #: The current indentation level (0 is default)
    indent = 0

    def __init__(self, **options) -> None:
        self.options = options or {}
        self._content = []

    def dump(self, method, obj, fp=None, indent=0, depth=None) -> None:
        # Prepare indentation level
        old_indent = self.indent
        self.indent = indent
        self.depth = depth or 0

        self._start()
        # Call the dump implementation
        method(obj)
        text = self._finish()
        (fp or sys.stdout).write(text)
        # reset indentation level
        self.indent = old_indent

    def _start(self) -> None:
        # Must be used in each method
        self._content.clear()

    def _finish(self) -> str:
        # Use this method to finish the current dumping process
        # and to retrieve the (highlighted content)
        text = "\n".join(self._content)
        if self.lexer is None or self.formatter is None:
            return text

        fmt_otps = self.options.get("fmt_opts", {})
        lex_opts = self.options.get("lex_opts", {})
        formatter = self.formatter(**fmt_otps)
        text = highlight(text, self.lexer(**lex_opts), formatter)
        return text

    def _line(self, text):
        pre = " " * self.indent
        self._content.append(pre + text)

    def _append(self, text):
        self._content[-1] += text

    def _dump_list(self, objects: list, cb, comment=None, indent=0, **kwargs):
        old_indent = self.indent
        self.indent = indent
        if comment and self.options.get("comments", True):
            self <<= f"// {comment}"

        for object in objects:
            cb(object, **kwargs)

        self.indent = old_indent
        self <<= ""

    def __lshift__(self, text) -> t.Self:
        self._append(text)
        return self

    def __ilshift__(self, line) -> t.Self:
        self._line(line)
        return self

# Not ready to use
class MemoryDump:
    def __init__(self, obj: Virtual) -> None:
        self.obj = obj
        self.binary = obj._fp.binary

    def save(self, name, align_to=None) -> None:
        with open(name, "wb") as fp:
            size = sizeof(type(self.obj), fp=self.obj._fp)
            data = self.binary.get_content_from_virtual_address(
                self.obj._address, max(size, align_to or 0)
            )
            fp.write(bytes(data))
