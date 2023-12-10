.. _abi_java:

================
Java Class Files
================

Although, the previously introduced ABI implementations to Objective-C and Swift
inspect executable files, this "ABI-like" module operates directly on Java class
files. The general structure of the Java class file won't be discussed here and
is fairly well documented on Oracle's documentation platform [#f1]_ .

.. code-block:: python
    :linenos:
    :caption: Example usage of the provided API

    from umbrella.java import JavaClassFile

    with open("/path/to/file.class", "rb") as fp:
        file = JavaClassFile(fp)

        # get the plain class name
        simple_name = file.get_simple_name()

        # iterator over all defined methods
        for method in file.jclass.methods:
            # retrieve the method's name
            name = file.get_constant_value(method.name_index)

        # iterate over all defined fields
        for field in file.jclass.fields:
            name = file.get_constant_value(field.name_index)
            access_flags: List[str] = field.access_flags.flags

        # list all class attributes
        for attribute in file.jclass.attributes:
            tag = attribute.name
            # based on the tag, each attribute should be handled differently
            ...


Structs
-------

:doc:`Constant Pool <constant_pool>`
    An overview of all used structs that occur in the constant pool.

:doc:`Access Flags <access_flags>`
    A list of all defined access flags for different types of constants or attributes.

:doc:`Attribute Structs <attribute>`
    All defined attribute structs (except StackFrameMap).


.. autoclass:: umbrella.java.ClassFile()
    :members:
    :undoc-members:

.. autoclass:: umbrella.java.JavaClassFile
    :members:
    :undoc-members:

.. toctree::
   :maxdepth: 1
   :hidden:

   access_flags
   constant_pool
   attribute




.. rubric:: Footnotes

.. [#f1] Java Virtual Machine Specification (`Class File Format <https://docs.oracle.com/javase/specs/jvms/se21/html/jvms-4.html>`_)