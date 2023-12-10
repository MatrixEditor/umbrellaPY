.. _introduction:

============
Introduction
============

As of today (2023), there are some tools in the wild that can be utilized to
restore the class layout of Objective-C and/or Swift binaries. Below is a short
list of useful tools and resources linked to this topic:

- `dsdump <https://github.com/DerekSelander/dsdump>`_: An improved class-dump implemented in Swift
- `icdump <https://github.com/romainthomas/iCDump>`_: Cross-platform parser of Objective-C metadata
- `ipsw <https://github.com/blacktop/ipsw>`_: Contains a Golang implementation of an Objective-C metadata parser
- `resymbol <https://github.com/paradiseduo/resymbol>`_: A reverse engineering tool to restore stripped symbol table and dump Objective-C class or Swift types for machO files.
- `SwiftDump <https://github.com/neil-wu/SwiftDump>`_: SwiftDump is a command-line tool for retriving the Swift Object info from Mach-O files.

However, there are some implementations for the Swift ABI, none of the packages
above provides a fully qualified parser for all metadata structs. In addition,
generic types are not supported (or at least not supported yet). Finally, most
of the projects are not available on all platforms and are therefore not
available to everyone.

This project ``umbrella`` (and ``umbrellacxx``) implements an API to inspect
static metadata of the Objective-C and Swift Runtime. Furthermore, it supports
inspecting 32-bit and 64-bit architecture binaries as well as MachO and portable
Executables as input files. The key features of this project are:

* Inspect static runtime information of Objective-C binaries.

    This includes a detailed restoration of Objective-C header files with
    classes, extensions, categories, and protocols. In addition, all runtime
    objects will be created and parsed in a lazy context and will be cached to
    minimize redundant parsing.

* Full and stable  Objective-C type decoder implementation.

* Inspect static runtime information of Swift binaries.

    This package covers a full python implementation of structures from the
    Swift ABI. They can be used to retrieve information on types (classes,
    enums, extensions, modules, and more), protocols, protocol conformances and
    builtin type definitions. The ABI also supports metadata structs for
    binaries of the ARM architecture (32-bit).

* Abstract classes for additional ABI implementations.

    The core API of this python package provides abstract base classes that can
    be used to implement another ABI for a programming language that stores
    static runtime information.

* Python implementation of TrailingObjects used within the Swift ABI (originated from LLVM) in order to support dynamic sized structures based on in-process information.

* Fully qualified Java class-file parser according to the Java SE21 specification

The following code snippet is an example of how easily this library can be
integrated.

.. code-block:: python
    :linenos:
    :caption: Example usage of umbrella-py

    from lief.MachO import parse, CPU_TYPES
    from umbrella.objc import ObjCMetadata
    from umbrella.swift import ReflectionContext

    binary = parse("/path/to/binary").take(CPU_TYPES.ARM64)
    objc = ObjCMetadata(binary)
    swift = ReflectionContext(binary)

    # Iterate over all classes
    for objc_Class in objc.classes:
        # inspect class data

    for swift_type in swift.types:
        # inspect classes, structs, enums, extensions, ....

