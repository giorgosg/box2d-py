# Changelog

The binding's version follows Box2D's: 3.2.0rc1 and 3.2.0 are built against
Box2D v3.2.0, and a fourth component, as in 3.2.0.1, is a release that changes
only the binding. See
[Installation](https://box2d-py.readthedocs.io/en/latest/getting_started/install.html#versions).

## Unreleased

- A world can make the application's own classes: `World(classes={Body:
  Ball})`, or `classes` on a World subclass, makes every body a `Ball`, and
  every object handed back is then one. `classes_with(mixin, Shape)` mixes
  one class into every shape kind, or every joint kind.
- `World.object_created` and `World.object_destroyed` report each body,
  shape, chain and joint the world and its bodies make, and each one's
  destroy, including everything a body, chain, mouse joint or world takes
  down with it: children first, and while still readable.
- The package ships `py.typed`, with its whole public API annotated.
- `b2_value` is gone from `box2d.accessors`; the properties that used it
  coerce on assignment, as the others do.

## 3.2.0rc1

The first release of these bindings for Box2D v3.2.0, and a release candidate:
the API may still change before 3.2.0. The 0.1.x releases on PyPI were an
earlier, incompatible binding of a development snapshot after Box2D v3.0.

- Bodies, every shape and chains; every joint type (distance, filter, motor,
  mover, pogo, prismatic, revolute, weld, wheel) plus a mouse joint.
- Sensor, contact, hit, body-move and joint events; pre-solve,
  pre-continuous, custom filter and material mixing callbacks.
- Collision queries and casts, 64-bit collision filters, and character
  movement, both geometric and with mover and pogo joints.
- Multithreaded stepping, profiling counters, capacity reporting and a
  deterministic state hash.
- Names follow Box2D's own, and so do defaults, except where the
  documentation says why not.
- A testbed of example scenarios, with an editor and console, that also
  runs in the browser.
- Wheels for Linux, macOS and Windows on Python 3.12 and later.

Not bound yet: world snapshots, and recording and replay.
