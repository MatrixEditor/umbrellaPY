.. _api_trailing_objects:

================
Trailing Objects
================

.. autoclass:: umbrella.trailing_objects.TrailingObjects
    :members:

    The classes defined above can be displayed virtually as follows:

    .. code-block:: text

        0          4  4          8  8         12
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ Foo      │  │ Bar      │  │ Bar      │
        ├──────────┤  ├──────────┤  ├──────────┤
        │ uint32 a │  │ uint32 x │  │ uint32 x │
        └──────────┘  └──────────┘  └──────────┘
                     ▲                          ▲
                     └──────────────────────────┘
                          Amount == Foo.a
