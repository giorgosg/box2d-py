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
- `World.write_moves(buffer)` writes the last step's moves into any writable
  buffer as packed 24-byte records, in C, keyed by the new `Body.key`: no
  Python object per body. `box2d.MOVE_RECORD` describes the record as a
  `struct` format, a numpy dtype and a field table. `World.write_transforms`
  writes the same record for every body, and `World.move_count` sizes the
  buffer.
- Definitions are data both ways. Each has a field table: `to_dict()` and
  `from_dict()` give JSON-ready dictionaries of what differs from the
  defaults (`full=True` for every field), strict about unknown keys;
  `def_from_dict()` makes shape and joint definitions by their `"kind"`;
  `fields()` describes each field's type, default, unit and range; and a
  definition's `repr` is code. `body.to_def()`, `shape.to_def()`,
  `chain.to_def()` and `joint.to_def()` read a live object back.
  `box2d.DEFAULTS_VERSION` names the set of defaults.
- Geometry definitions take `shape=`, a `ShapeDef`, and `body.add_shape()`
  makes a shape or chain from a definition, as `world.add_body_def()` does a
  body. `BodyDef` and `BoxDef` are exported at the top level, and `BodyDef`
  takes its type as a name and its rotation as an angle.
- Definitions compare by what Box2D would make of them: a field left as None
  equals its default, and floats compare as 32-bit floats. `CollisionFilter`
  compares by category, mask and group.
- `InvalidInputError` is data as well as a message: `function` and
  `condition` give Box2D's own function and check, `field` the Python name of
  the definition field, property or argument refused, and `value` what it
  held. Field tables give the C names of geometry definitions too.
- Assigning `Body.mass_data` works; it always raised a `TypeError`.
- The testbed is its own package, `box2d-testbed`, so `box2d-python` no longer
  carries it: the `testbed` extra installs it, and the `box2d-testbed` command
  comes with it.
- A WebAssembly wheel for Pyodide 0.29 is built with every release, and held
  to a budget for its size and import time.
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
