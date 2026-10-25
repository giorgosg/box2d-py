Writing scenarios
=================

A scenario is a class, and a scenario file is a Python module that defines
one or more. The testbed's own, in ``box2d_testbed/tb_*.py``, are written the
way this page describes, and open in its editor to read or to copy from.

What a scenario looks like
--------------------------

Declaring a subclass of ``BaseTest`` registers it, under the category and the
name it gives; the Tests panel lists it there. This one drops a box from a
height chosen in its panel:

.. code-block:: python

    from box2d_testbed.base_test import BaseTest, UI


    class Drop(BaseTest, category="Bodies", name="Drop"):
        """A box dropped onto the ground from a height you choose.

        Watch it settle: Box2D puts a body to sleep once it has been still for a
        moment, and the status line says when that happens.
        """

        camera_center = (0, 5)
        camera_zoom = 12.0

        drop_height = UI.float(8.0, min=1.0, max=20.0)

        def setup(self):
            self.world.new_body().static().segment((-20, 0), (20, 0)).build()
            self.box = (
                self.world.new_body()
                .dynamic()
                .position(0, self.drop_height)
                .box(1, 1, friction=0.4)
                .build()
            )

        @drop_height.callback
        def on_drop_height(self, key, value):
            # Where the box starts is part of building the scene, so build it again.
            self.rebuild()

        def status(self):
            return "asleep" if not self.box.awake else f"height {self.box.position.y:.1f}"

A category can hold any number of scenarios, and a scenario declared with the
category and name of one already registered takes its place. The class name
is the file's own business: the testbed shows the ``name``.

Building the scene
------------------

``setup`` builds the scene in ``self.world``, a world the testbed has made
with the Controls panel's settings. It is the one method a scenario has to
define.

``self.rebuild()`` throws the scene away and builds it again: it destroys the
world, makes a new one -- in the testbed, with the Controls panel's settings
as they are then -- and calls ``setup`` again in it. Reset in the scenario's
panel does the same. The controls keep their values, so ``setup`` builds with
whatever they are set to now, and the view stays where it was.

A new world rather than the old one emptied, because that is what makes the
rebuilt scene run step for step as it first did -- unless it was built from
Python's random numbers, which come out differently each time. It also means
``self.world`` is a different object after a rebuild, so read it when it is
needed rather than keeping it, and set anything the scene needs on the world,
such as its gravity or a callback, in ``setup``, where it is set again on
each new world.

Controls
--------

Each ``UI`` declaration on the class is a control in the scenario's panel,
below the Reset and Reset View buttons every scenario has, in the order they
are declared. Each is labelled with its attribute's name in title case,
``drop_height`` as "Drop Height", unless given a ``label=``.

.. list-table::
   :widths: 40 60

   * - ``UI.float(default, min=, max=)``
     - A slider of floats, between ``min`` and ``max``.
   * - ``UI.int(default, min=, max=)``
     - A slider of whole numbers. Both sliders need their ``min`` and
       ``max``, which are their ends.
   * - ``UI.bool(default)``
     - A checkbox.
   * - ``UI.select(default, options)``
     - A drop-down of the strings in ``options``.
   * - ``UI.button(label)``
     - A button.

A control reads as an attribute: ``self.drop_height`` is the slider's value
now. Setting the attribute from code, as the console can, moves the control
too.

``@control.callback`` registers a method to run when the control changes, as
``on_drop_height`` does above. It is called as ``callback(self, key, value)``,
with the attribute's name and its new value, and only once the scene has been
built: a control set before ``setup``, or while it runs, stores its value for
``setup`` to read and runs nothing. So a callback can rely on everything
``setup`` makes. A button has no value worth reading: its callback is what it
does.

A callback whose control changes how the scene is built, such as where a body
starts, calls ``self.rebuild()``. One whose control tunes something in place,
such as a motor's speed, sets it on what is already there.

What the scenario shows
-----------------------

``status()`` returns a line of text, a list of lines, or None for none,
called every frame and shown at the top left of the view. It stays put as the
camera moves.

``debug_draw(debug_draw)`` is called every frame after the world has been
drawn, with the testbed's renderer, to draw in the world as well: its
``draw_segment``, ``draw_point``, ``draw_solid_capsule``, ``draw_string`` and
the other methods of :class:`~box2d.debug_draw.DebugDraw`, in world
coordinates and with a :class:`~box2d.debug_draw.Color`. What is drawn there
moves with the camera.

``camera_center`` and ``camera_zoom`` frame the scenario when it opens:
the point at the centre of the view, and half the height of the view, in
metres. Leave either out and it is worked out from the bodies that can move,
or from the whole scene if none can. The **Copy** button in the status bar
copies the current view as these two lines.

Each step and each input
------------------------

``after_step(dt)`` is called after every step of the world, with the step's
length in seconds. It is where a scenario does what Box2D does not: reads
events, moves a kinematic body, or steers a character.

``on_key_down(key)`` and ``on_key_up(key)`` are called with the name of a key
pressed or released over the simulation: a letter ``"a"`` to ``"z"``, a digit
``"0"`` to ``"9"``, or one of ``"space"``, ``"left"``, ``"right"``, ``"up"``,
``"down"``, ``"escape"``, ``"enter"`` and ``"tab"``. ``P``, ``O`` and ``R``
also reach the testbed, which pauses, steps and resets on them, so a scenario
does best to leave them alone.

``on_mouse_down(pos)``, ``on_mouse_drag(pos, rel)`` and
``on_mouse_release(pos)`` are called for the left button, with the pointer's
position in the world as a :class:`~box2d.math.Vec2`, and for a drag how far
it moved since the last frame, in pixels. ``BaseTest``'s own are what pull a
body about with the mouse, so a scenario that overrides them and still wants
that calls ``super()``.

Running one without the window
------------------------------

A scenario needs nothing from the window: it is built on any world, and
stepped by stepping that world. This is how the project tests its own, and a
quick way to check one:

.. code-block:: python

    >>> from box2d import World
    >>> world = World()
    >>> drop = Drop(world)
    >>> drop.setup()
    >>> drop.status()
    'height 8.0'
    >>> for _ in range(600):
    ...     drop.world.step(1 / 60, 4)
    >>> drop.status()
    'asleep'

Setting a control runs its callback, as moving the slider would, and this one
rebuilds the scene in a new world, with the box at its new height:

.. code-block:: python

    >>> drop.drop_height = 3.0
    >>> drop.status()
    'height 3.0'
    >>> world.is_valid, drop.world.is_valid
    (False, True)

The testbed calls ``after_step`` after each step; a loop like this one calls
it itself if the scenario has one.

Where scenarios live
--------------------

Your scenarios are ordinary Python files, loaded at startup beside the shipped
ones, from a directory of their own:

.. list-table::
   :widths: 20 80

   * - Linux
     - ``~/.local/share/box2d-testbed/scenarios``, or under
       ``$XDG_DATA_HOME`` if that is set
   * - macOS
     - ``~/Library/Application Support/box2d-testbed/scenarios``
   * - Windows
     - ``%APPDATA%\box2d-testbed\scenarios``

The ``BOX2D_TESTBED_SCENARIOS`` environment variable points the testbed at
another directory instead, such as one in a project of your own. The Scenario
menu shows which directory is in use.

A file's name, less the ``.py``, has to be a Python identifier of up to 64
characters; other files there are left alone. A file is run on its own rather
than as part of a package, so it imports the testbed as any other program
would, with ``from box2d_testbed.base_test import BaseTest, UI`` rather than a
relative import. A file that does not load at startup is skipped, with a line
in the terminal saying why, and the rest load as usual.

The editor
----------

The **Editor** tab, beside Simulation, edits scenario files. Its drop-down
picks the file, from your directory (``user/``) and from the shipped
scenarios (``builtin/``), which open read-only. Where sharing is on, as in the
browser, scenarios opened from a link are listed too (``shared/``);
:doc:`browser` covers those.

- **New** writes a new file to your directory, ``untitled.py`` or the next
  free name after it, from a template much like ``Drop`` above, and runs it.
- **Fork** copies what is open, edits included, into your directory under
  the same name with ``_copy`` added, and runs the copy. It renames the
  scenarios in it, ``Drop`` to ``Drop copy``, so the copy appears beside the
  original instead of taking its place, and rewrites a shipped scenario's
  relative imports so the file stands alone. Forking is how a shipped
  scenario becomes one you can change; the Scenario menu's **Edit the running
  one** finds the file behind what is on screen.
- **Save**, or ``Ctrl+S`` while the editor has the keyboard, writes the file
  and runs it.
- **Run** runs what is in the editor without writing it.
- **Revert** throws the edits away, back to the file as last saved, and
  **Delete** deletes the file, after asking.

Running a file replaces whatever it registered the last time it ran, and puts
its scenario on screen in a new world, framed as it opens and with its
controls at their defaults -- the same scenario if the file has several and
one of them was already running. So the
loop is edit, ``Ctrl+S``, watch, with nothing restarted. A file run this way
lasts until the testbed closes; the next start loads what is saved.

When something goes wrong
-------------------------

A scenario being edited is a scenario that breaks, and the editor holding the
fix is inside the testbed, so the testbed catches the errors a scenario
makes at the points it is most likely to make them:

- **A file that will not compile, or raises as it runs**, is reported in the
  editor: the message above the source, a marker on the line, and the
  traceback under it. Whatever was registered and running before stays as it
  was. Saving still writes the file, so nothing typed is lost.
- **A setup that raises**, when the testbed opens a scenario or runs its
  file, stops the scenario there: whatever it built before raising stays in
  the world, but none of the scenario's methods are called, and the
  traceback is in its panel and the terminal. Fix the file and run it again.
- **after_step, status or debug_draw raising** is reported once, in the
  scenario's panel and the terminal, and that one method is not called again
  until the scene is built again, by Reset or by running the file. The rest
  of the scenario carries on, so a broken status line neither stops the
  scene nor prints a traceback every frame.

Other exceptions are not caught. One raised by a control's callback, by a key
or mouse handler, or by ``setup`` when Reset or a callback runs it again,
closes the testbed, with the traceback in the terminal.
