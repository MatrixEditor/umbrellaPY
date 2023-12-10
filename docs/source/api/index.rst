.. _api_index:

========================
API Concepts & Reference
========================

In the following chapters you will learn about the basement of this library. Each section
describes another feature that can be used to built new ABI implementations for other
languages. Each sub-page contains details on how to use classes mentioned in the next
sections (make sure to take a closer look if you want to implement a new metadata reader).

The basic workflow of each implementation can be visualized as follows:

.. code-block:: text
    :caption: Metadata Reader Workflow

                             ┌───────────────────────────────┐
     ┌──────────┐            │                               │
     │          │   Input    │   Custom ABI Implementation   │
     │  Binary  ├───────────►│          <extends>            │
     │          │ using lief │           Runtime             │
     └──────────┘            │                               │
                             └──────────────┬────────────────┘
                                            │ using construct
                                            │ using construct-dataclasses
                                            │
                                            ▼
                                ┌──────────────────────────┐
                                │                          │
                                │   Metadata Information   │
                                │                          │
                                └──────────────────────────┘

The produced metadata information may store all parsed data directly, or it uses umbrella's
API components to parse the information only if requested. Each ABI implementation must
extend the :class:`DataStream` class to support basic parsing operations. The abstract
:class:`Runtime` class provides default methods on parsing structs, dataclass structs,
strings and pointer sections. In addition, the :class:`Runtime` class supports different
binary formats and adapts parsing based on the used binary.

The user should retrieve all metadata information by providing the parsed binary. The
following example illustrates the process on a Swift binary:

.. code-block:: python
    :linenos:
    :caption: Basic process of parsing a binary storing Swift metadata information

    from lief.MachO import parse, CPU_TYPES
    from umbrella.swift import ReflectionContext

    binary = parse("/path/to/binary").take(CPU_TYPE.ARM64)
    context = ReflectionContext(binary)
    # further processing ...

.. note::
    Each class derived from :class:`Runtime` must be initialized with the parsed binary
    instance. That enables us more flexibility of operations on the target binary.
    Furthermore, we enable multiple ABI implementations to work on the same binary instance
    to reduce redundant parsing.


Virtual Memory Objects
----------------------

All parsed structures *should* inherit the :class:`Virtual` class to get identified as virtual
memory objects. They are special as they store the object's virtual memory address after parsing
has completed. In addition, in order to enable further processing, the parser instance is saved
as well. Using a runtime object, one can simply get the binary content of an object marked as
virtual:

.. code-block:: python
    :linenos:

    from umbrella.runtime import sizeof

    # assume we use the parsed object here
    obj = ...
    content: bytes = context.read_raw(obj._address, sizeof(obj))

These fields will be more relevant later on when inspecting Swift type metadata. For now, it's
enough to know that we organize all structs as objects of the :class:`Virtual` class. In
addition, there is a :class:`VirtualMemoryBlock` that supports parsing structs or construct
objects within the *"virtual"* memory.

.. code-block:: python
    :linenos:

    from umbrella.runtime import Runtime

    runtime = Runtime(...)
    # virtual memory block object will be created automatically
    result = (runtime+FooStructClass) @ 0xdeadbeef


Caching Iterators
-----------------

The (as for now) two ABI implementations of Objective-C and Swift use lazy parsing of their
structs to reduce the overall parsing time. They are using a :class:`CachingIterator` to
automatically cache their parsed objects.

.. note::
    It is recommended to use these types of iterators instead of plain lists in order to save
    time when you want to access specific components. Anyways, you can just use ``all()`` to
    retrieve a list of all parsed structs.


Dumper
------

Finally, there is an abstract dumper template that can be used to implement a "class-dump" like
class. It is intended to simplify the process of generating and writing output to an ``IOBase`` object. In
addition, it integrates ``pygments`` to colorize the created text. For specific notes and
information about the :class:`IDumper` class, please refer to its section.


API Components
--------------

:doc:`Basic Runtime API <runtime>`
   Standard API classes that form the basement of this library

:doc:`Iterator Types <iterator>`
   A small collection of iterator types that enable caching and lazy parsing.

:doc:`Flags <flags>`
   In introduction on how flags can be handled and integrated with a custom class.

:doc:`Dump <dump>`
   The dumper architecture for this library.

:doc:`Trailing Objects <trailing_objects>`
   A review of how we implemented ``TrailingObjects`` in pure Python.





