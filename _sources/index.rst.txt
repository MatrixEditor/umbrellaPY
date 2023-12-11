Umbrella's documentation
========================

The *Umbrella* project delivers different modules that can be utilized to
inspect static runtime information to mimic a language specific ABI. All
modules are implemented in pure Python.

.. note::
   A C++ package to inspect the Objective-C runtime can be found here:
   `umbrellacxx <https://github.com/MatrixEditor/umbrella>`_.

Using this library
------------------

:doc:`introduction`
   Overview of the ``umbrella`` Python Package, simple usage examples and an overview of documentation structure.

:doc:`installation`
   How to install the python package, build the documentation and setup the development environment.

:doc:`Core API <api/index>`
   Introduction to the underlying API and usage examples.


Application Binary Interface
----------------------------

:doc:`ABI Implementations <abi/index>`
   A list of all implemented and documented ABIs.

:doc:`Examples <examples/index>`
   A small collection of usage examples.


Development
-----------

:doc:`roadmap`
   The current development status and roadmap.

:doc:`contributing`
   General Guidelines on Contributing to the Project

:doc:`Development guidelines <development>`
   Guidelines for Developers on Developing and Testing Changes.

:doc:`changelog`
    The package development changelog.


.. toctree::
   :maxdepth: 3
   :caption: Using this Library
   :hidden:

   introduction
   installation
   api/index
   abi/index
   examples/index

.. toctree::
   :maxdepth: 3
   :hidden:
   :caption: API Components

   api/runtime
   api/iterator
   api/flags
   api/dump
   api/trailing_objects

.. toctree::
   :maxdepth: 3
   :caption: ABI Implementations
   :hidden:
   :numbered:

   abi/swift/index
   abi/objc/index
   abi/java/index

.. toctree::
   :maxdepth: 3
   :caption: Development
   :hidden:

   roadmap
   contributing
   development
   changelog

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
