.. _api_iterator:

=========
Iterators
=========

This document tries to provide a compact overview of the generic iterators
provided by this package. Each iterator class may be extended, so that it
can be used within a new feature implementation.

.. autoclass:: umbrella.iterator.CachingIterator
    :members:
    :private-members: _load
    :special-members: __len__

.. autoclass:: umbrella.iterator.LazyIterator
    :members:
    :private-members: _preload_context

.. autoclass:: umbrella.iterator.ReflectionSectionIterator
    :members: