.. _abi_objc:

===============
Objective-C ABI
===============

The following sections are going to introduce the Objective-C binary structure with
its binary sections and structs. As each struct definition is mapped to an actual Python
class, they will be displayed together. Furthermore, this ABI implementation explicitly
supports 32-bit and 64-bit binaries - the struct will be chosen according to the currently
used binary.

To get more information about the type encoding used by Apple in Objective-C binaries,
please refer to their website: `Type Encodings <https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/ObjCRuntimeGuide/Articles/ocrtTypeEncodings.html>`_.

.. note::
    All classes documented here will refer to a 64-bit architecture binary if both 64-bit
    and 32-bit structures don't differ in the number of their fields (only pointer size has
    changed). For a list of annotated types, please refer to :ref:`runtime_types`.


Objects
-------

The base for all Objective-C structs that can be instantiated will be the :class:`TargetObjCObjectRaw64`
and :class:`TargetObjCObjectRaw32`. Structs extending an Objective-C object structure
store a pointer to the class/protocol or category definition of which the object of this
struct is an instance (also known as an *isa* pointer). For instance, the protocol A will
store a reference to the protocol class A which stores class-level properties and
methods.

.. autoclass:: umbrella.objc.TargetObjCObjectRaw64
    :members:

Classes
-------

According to Apple's developer documentation, "a class describes the behavior and
properties common to any particular type of object". [#f1]_ They can be defined as blueprints
for actual objects. Internally, classes first define their super class, cache, an
optional vtable and their data as references with pointers.

.. autoclass:: umbrella.objc.TargetObjCClassRaw64()
    :members:

Each class data reference stores additional information in its top bits. Therefore, an
additional data structure is used to determine the actual location of the class data.

.. autoclass:: umbrella.objc.ClassDataBits64()
    :members:
    :inherited-members:

Class Data
~~~~~~~~~~

The internal class data is responsible for providing information about the defined instance
variables, methods and properties as well as the conforming protocols. Note that the following
class describes the class data on 64-bit architectures. It includes an additional field named
*reserved*.

.. autoclass:: umbrella.objc.TargetClassDataRaw64()
    :members:


Class Model
~~~~~~~~~~~

After parsing the data, the Python API will create an instance of :class:`ObjCClass` which
stores all relevant information about the class.

.. autoclass:: umbrella.objc.ObjCClass()
    :members:


Methods
-------

"Methods are the primary way an object manipulates and provides access to its state". [#f3]_ Internally,
they are represented through a simple struct that stores the method's name, signature and implementation
address.

.. autoclass:: umbrella.objc.TargetMethodRaw64()
    :members:


.. autoclass:: umbrella.objc.ObjCMethod()
    :members:


.. note::
    *Small* methods store pointers (``int32_t``) relative to the struct's address.


Properties
----------

Properties in Objective-C provide a public access interface to a class. Their internal structure is
even more simple than the previously introduced method structure: They just store the name and
attributes as a string.

.. autoclass:: umbrella.objc.TargetPropertyRaw64()
    :members:


.. autoclass:: umbrella.objc.ObjCProperty()
    :members:


Instance Variables
------------------

The primary way to maintain the internal state of an object can be done by defining instance
variables.

.. autoclass:: umbrella.objc.TargetIVarRaw64()
    :members:

.. warning::
    Be aware that sometimes the name and encoded type of an instance variable must be swapped before
    using them - no idea why. Automatic swapping will be applied while parsing IVars.

.. autoclass:: umbrella.objc.ObjCIVar()
    :members:


Protocols
---------

Objective-C protocols are used to declare properties and methods that are independent from any other
class. They can be seen as interfaces in terms of the Java language, except this type can define
required and optional methods, both class and instance ones. Fortunately

.. autoclass:: umbrella.objc.TargetProtocolRaw64()
    :members:

.. autoclass:: umbrella.objc.ObjCProtocol()
    :members:


Categories and Extensions
-------------------------

Categories in Objective-C add methods (and properties) to an existing class. There are two types of
categories: Anonymous Categories (Extensions) and default Categories.

.. autoclass:: umbrella.objc.TargetCategoryRaw64()
    :members:

.. autoclass:: umbrella.objc.ObjCCategory()
    :members:


For a detailed overview of all structs mentioned in this document, please refer to
`runtime-new.h <http://opensource.apple.com/source/objc4/objc4-532/runtime/objc-runtime-new.h>`_ of
the official Apple Source Code.

*TODO: Metadata, Dumper*

.. rubric:: Footnotes

.. [#f1] Apple developer documentation on `Defining Classes <https://developer.appl.com/library/archive/documentation/Cocoa/Conceptual/ProgrammingWithObjectiveC/DefiningClasses/DefiningClasses.html#//apple_ref/doc/uid/TP40011210-CH3-SW1>`_
.. [#f2] Objective-C `Class <https://developer.apple.com/documentation/objectivec/class?language=objc>`_
.. [#f3] objc-guide: `Methods and Implementations <https://microsoft.github.io/objc-guide/MethodsAndImplementations.html>`_
.. [#f4] Objective-C `Property <https://developer.apple.com/documentation/objectivec/objc_property_t?language=objc>`_