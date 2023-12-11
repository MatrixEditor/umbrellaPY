.. _swift_abi_enums:


============================
Reconstruction of Swift Code
============================

Enums
-----

.. tab:: Original Enum

    .. code-block:: swift
        :linenos:

        public enum Foo<T: Bar, U, V, W> {
            case bar
            case baz(param: String)
            case foobar(Int32)
        }

.. tab:: Re-Created Enum

    .. code-block:: swift
        :linenos:

        public enum test.Foo<A, B, C, D> {
            // Cases: 3, 1 empty
            case baz(param: Swift.String)
            case foobar // $s\x02_\x91\xff\xff
            case bar
        }


=========
Protocols
=========


.. tab:: Original Protocol

    .. code-block:: swift
        :linenos:

        public protocol Bar: Foo, Equatable {
            associatedtype Baz
            associatedtype FooBar

            var id: UInt64 { get set }
        }


.. tab:: Re-Created Protocol

    .. code-block:: swift
        :linenos:

        public protocol test.Bar: A, B where B: Foo {
            associatedtype Baz
            associatedtype FooBar
            // 7 Requirements
            // static var BaseProtocol
            // static var BaseProtocol
            // static var AssociatedTypeAccessFunction
            // static var AssociatedTypeAccessFunction
            // var Getter
            // var Setter
            // var ModifyCoroutine
        }

