.. _api_runtime:

==============
Static Runtime
==============

This document aims to provide a detailed guide on internal classes used to organize
the parsed metadata.

Public Interface
~~~~~~~~~~~~~~~~

.. autofunction:: umbrella.runtime.get_context_value

    Note that this method is used within the :class:`Virtual` object creation. You can
    use it to search for a value within a context that has been set in the parent context.

.. autofunction:: umbrella.runtime.__x64__

.. autofunction:: umbrella.runtime.sizeof

    Examples:

    >>> from umbrella.runtime import sizeof
    >>> sizeof(Virtual) # type reference
    0
    >>> sizeof(construct.Int32ul) # struct reference
    4

.. _runtime_types:

Types
~~~~~

The following table serves as a reference for annotated types in structs. It tries to illustrate
each type's size.

.. list-table:: Runtime Types
    :header-rows: 1
    :widths: 10, 10, 5, 20

    * - Name
      - Size (in bytes)
      - Python Type
      - Info
    * - Void
      - NaN
      - ``construct.Contruct``
      - This object represents an incomplete type that can be used within relative pointers (see Swift ABI)
    * - int8_t
      - 1
      - ``int``
      - signed char
    * - uint8_t
      - 1
      - ``int``
      - unsigned char
    * - int16_t
      - 2
      - ``int``
      - signed short
    * - uint16_t
      - 2
      - ``int``
      - unsigned short
    * - int32_t
      - 4
      - ``int``
      - signed integer
    * - uint32_t
      - 4
      - ``int``
      - unsigned integer
    * - int64_t
      - 8
      - ``int``
      - signed long
    * - uint64_t
      - 8
      - ``int``
      - unsigned long
    * - uintptr_t
      - 4 or 8
      - ``int``
      - Pointer type with a size of 8 bytes on 64-bit architectures and 4 on 32-bit ones.




Abstract Classes
~~~~~~~~~~~~~~~~

.. autoclass:: umbrella.runtime.DataStream
    :members: read_struct, read_raw

The next classes will be more important as they can be used as markers to trigger special
struct parsing.

.. py:class:: umbrella.runtime.CString

    A typing class that can be used to mark pointers to strings in virtual memory. Note
    that the returened string instance won't store the zero termination character at the
    end. As this class is marked to be a singelton instance, you can reference it
    directly. Be aware that the following code won't work:

    .. code-block:: python
        :linenos:

        from umbrella.runtime import CString

        @dataclass
        class Foo:
            name: str = csfield(CString) # !!! DON'T DO THAT

    Due to the fact that this class is only a template/marker we can't use it for parsing
    purposes directly.

    .. code-block:: python
        :linenos:

        from umbrella.runtime import CString

        runtime = Runtime(...)
        objc: str = runtime.read_struct(CString, 0x1234) # Thats the right way

    .. autofunction:: umbrella.runtime.CString.is_cstring


.. py:class:: umbrella.runtime.RawCString

    A typing class that can be used to mark pointers to zero terminated bytearrays in
    virtual memory.

    .. autofunction:: umbrella.runtime.RawCString.is_raw_cstring



.. autoclass:: umbrella.runtime.Virtual
    :members:

.. autoclass:: umbrella.runtime.VirtualMemoryBlock
    :members:

.. autoclass:: umbrella.runtime.VirtualArray
    :members:

.. autoclass:: umbrella.runtime.AlignedUnion
    :members:

.. autoclass:: umbrella.runtime.Runtime
    :members: