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

import typing as t

from umbrella.runtime import BinaryFile
from umbrella.java import ClassFile, attribute

class JavaClassFile(BinaryFile):
    def __init__(self, __stream: str) -> None:
        super().__init__(__stream)
        self._class = (self+ClassFile) @ 0x00

    @property
    def jclass(self) -> ClassFile:
        """The underlying java class file"""
        return self._class

    # TODO: more utility methods
    def get_simple_name(self) -> str:
        """Returns only the class name.

        :return: the simple name of the underlying class
        :rtype: str
        """
        return self.jclass.get_name().split("/")[-1]

    def get_package_name(self) -> str:
        """Generates the package name for the underlying class.

        :return: the package name (e.g. ``"com.example.foo"``)
        :rtype: str
        """
        return ".".join(self.jclass.get_name().split("/")[:-1])

    def get_source_name(self) -> t.Optional[str]:
        """Returns the source code file name (if present)

        :return: the source code file name
        :rtype: t.Optional[str]
        """
        attr = self.get_attribute("SourceFile")
        if attr is not None:
            return self.get_constant_value(attr.info.index)

    def get_attribute(self, kind: str) -> t.Optional[attribute.AttributeInfo]:
        """Tries to retrieve the first attribute with the given kind.

        :param kind: the attribute info tag (string)
        :type kind: str
        :return: the first occurrence of the given attribute kind
        :rtype: t.Optional[AttributeInfo]
        """
        for attribute in self.jclass.attributes:
            if attribute.name == kind:
                return attribute

    def get_constant_value(self, index: int) -> t.Union[str, int, float, t.Any]:
        """Returns the value associated to a constant entry.

        :param index: the constant pool relative index (starts with 1)
        :type index: int
        :return: the value or info object of no "value" field is defined
        :rtype: t.Union[str, int, float, t.Any]
        """
        info = self.jclass.get_constant(index)
        return getattr(info, "value", info)