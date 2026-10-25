Lifetime and Errors
===================

Every wrapper checks, each time it is used, that the Box2D object it names
still exists. Once that object is gone -- destroyed itself, or taken down with
its body or world -- using the wrapper raises :exc:`~box2d.lifetime.DestroyedError` rather
than reaching into freed memory. An argument Box2D rejects raises
:exc:`~box2d.InvalidInputError`. Both are importable from ``box2d``.

.. autoexception:: box2d.lifetime.DestroyedError

.. autoexception:: box2d.InvalidInputError
