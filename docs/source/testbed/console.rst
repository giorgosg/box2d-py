The console
===========

The **Console** panel along the bottom of the testbed is a Python prompt on
the running simulation. A scenario's controls are the ones it declared in
advance; the console is for everything else: reading a body's velocity or a
joint's force, moving something, adding a shape and watching it fall, trying a
setting before giving it a control.

What is in scope
----------------

These names are bound to what is running:

.. list-table::
   :widths: 20 80

   * - ``test``
     - The running scenario, the instance of its class.
   * - ``world``
     - The world it runs in.
   * - ``state``
     - The testbed's settings and view: ``state.simulation_paused``, ``state.hertz``,
       ``state.center`` and the rest of what the Controls panel shows.
   * - ``app``
     - The testbed application itself, its panels included.

They are bound again before every command, so they follow a reset, a rebuild
or another scenario being opened: ``world`` is always the world on screen,
never one a reset has destroyed. ``box2d`` and ``Vec2`` are imported, and
names you define stay defined from one command to the next. **Reset names**
clears everything you defined, leaving just these.

Say the ``Drop`` scenario from :doc:`scenarios` is open, and paused with
``P``, so that nothing moves between one command and the next. Its world, and
anything in it, can be read and changed directly:

.. code-block:: python

    >>> test.name
    'Drop'
    >>> len(world.bodies)
    2
    >>> test.box.linear_velocity = (3, 10)
    >>> test.box.linear_velocity
    Vec2(3.0, 10.0)
    >>> for body in world.bodies:
    ...     print(body.type)
    ...
    static
    dynamic

Setting one of its controls moves the control in its panel and runs its
callback, as dragging the slider would, so this rebuilds the scene with the
box 15 m up -- where it stays, until the simulation is resumed:

.. code-block:: python

    >>> test.drop_height = 15.0
    >>> test.box.position.y
    15.0

What a command prints, and the value of an expression, appear in the panel
above the prompt, and so does the traceback of a command that raises.
Nothing typed here can close the window: ``exit()``, or anything else that
raises ``SystemExit``, is reported and ignored.

Keys
----

.. list-table::
   :widths: 20 80

   * - ``Enter``
     - Run what is at the prompt, or start another line if it is not a whole
       statement yet.
   * - ``Tab``
     - Complete the name left of the cursor, or indent if there is none.
   * - ``Ctrl+R``
     - Search what you have run.
   * - ``Up`` ``Down``
     - Walk back and forward through what you have run, while the prompt is
       one line. In a block of several lines they move the cursor instead.

Enter follows the rule any Python prompt does. A complete statement runs. One
that is not complete yet, such as ``for body in world.bodies:``, takes another
line, and so does each line inside the block it opens; Enter on the empty
line after it closes the block and runs it, whether it was typed or pasted.

``Ctrl+R``, or the **History** button, opens a search over what has been run.
Type part of a command to find the newest one containing it, and press Enter
to put it at the prompt, or Escape to leave the prompt as it was.

Completion
----------

Tab completes on the live objects. To complete ``world.bo``, the console
evaluates ``world`` and lists what that object actually has, so
``world.`` offers the running world's own attributes rather than guesses.

When one name matches, Tab puts it in. When several do, Tab fills in as much
as they have in common, and lists them under the prompt, the first twelve and
a count of the rest. Since completing evaluates everything before the last
dot, complete a name rather than the result of a call: ``test.box.`` is
cheap to evaluate, but whatever is left of the dot runs each time Tab is
pressed. If evaluating it fails, nothing is completed.

Copying
-------

The output above the prompt is text that can be selected, as in an editor:
drag across it, or double-click a word, then press ``Ctrl+C``. Clicking in the
output without selecting anything puts the keyboard back at the prompt.
**Clear** empties the output; it keeps the last 2000 lines in any case.
