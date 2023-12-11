.. _examples_root:

========
Examples
========

Below is a list of usage examples and small snippets that illustrate how this library
can be utilized.

Objective-C Class-Dump
----------------------

The class-dump of Objective-C classes is rather easy. You can follow the next script
to dump all defined classes in a binary:

.. code-block:: python
    :linenos:
    :caption: Example implementation of an Objective-C class dump

    from lief import MachO
    from umbrella.objc import ObjCMetadata, ObjCDumper

    binary = MachO.parse("/path/to/binary").take(MachO.CPU_TYPES.ARM64)
    metadata = ObjcMetadata(binary)
    dumper = ObjCDumper()

    for objc_class in metadata.classes:
        with open(f"{objc_class.name}.h", "w", encoding="utf-8") as fp:
            dumper.dump_class(objc_class, fp)


Swift Class-Dump
----------------

The following code-snippet may be used as an entrypoint for writing complete class-dumps
of Swift metadata.

.. code-block:: python
    :linenos:
    :caption: Example implementation of a Swift class dump

    from lief import MachO # actually, PE and ELF are supported as well
    from umbrella.swift import ReflectionContext, has_swift_metadata, SwiftDumper

    binary = MachO.parse("/path/to/binary").take(MachO.CPU_TYPES.ARM64)
    if has_swift_metadata(binary):
        # To be sure a binary stores swift metadata, use has_swift_metadata(...)
        metadata = ReflectionContext(binary)
        dumper = SwiftDumper()
        # Unfortunately, all types (classes, structs, enums, protocols, ...) are
        # stores within one large array. We have to filter them:
        for cls in metadata.classes():
            name: str = cls.get_mangled_name()
            with open(f"{name}.h", "w", encoding="utf-8") as fp:
                dumper.dump_class(cls, fp=fp)


A sample output may be the following:

.. tab:: Original Swift code

    .. code-block:: swift
        :linenos:

        public class Bar {
            public func x() -> String {...}
            public func y() -> Int64 {...}
        }

        public class Foo: Bar {
            public let i = 0;
            var someLongVariableName = 1;
            private func indexed() -> Int {...}
            public override func x() -> String {...}
            public override func y() -> Int64 {...}
        }

.. tab:: Reversed Structure from Metadata

    .. code-block:: swift
        :linenos:

        public class main.Bar {
            // Methods
            /* 0x1270 */ public func x() -> Swift.String
            /* 0x12a0 */ public func y() -> Swift.Int64
            /* 0x1320 */ static func <stripped> // Init
        }
        public class main.Foo: ? {
            // Properties/Fields
            let i: Swift.Int
            var someLongVariableName: Swift.Int

            // Methods
            /* 0x13a0 */ func someLongVariableName.getter : Swift.Int // (stripped)
            /* 0x13f0 */ func someLongVariableName.setter : Swift.Int // (stripped)
            /* 0x1440 */ func someLongVariableName.modify : Swift.Int // (stripped)
            /* 0x14b0 */ func <stripped> // Method
            // Overridden functions
            /* 0x14cc */ public override func x() -> Swift.String // from main.Bar
            /* 0x14fc */ public override func y() -> Swift.Int64 // from main.Bar
            /* 0x151c */ static override func <stripped> // Init from main.Bar
        }
