Running the testbed
===================

The testbed is a window of scenarios, each a small scene showing one part of
Box2D -- stacking, shapes, joints, events, continuous collision, character
movement -- running live, with its own controls beside it. It also has an
editor for writing scenarios of your own, described in :doc:`scenarios`, and
a Python console on the running simulation, described in :doc:`console`.

Installing and starting it
--------------------------

The testbed is the ``testbed`` extra, which adds imgui, PyOpenGL and numpy to
the package:

.. code-block:: bash

    pip install "box2d-python[testbed] @ git+https://github.com/giorgosg/box2d-py.git"

It installs a ``box2d-testbed`` command, which opens the window on the first
scenario:

.. code-block:: bash

    box2d-testbed

:doc:`../getting_started/install` covers what the install needs. The testbed
also runs in a browser, with a few differences :doc:`browser` describes.

The window
----------

**Simulation** is the view of the running scene. It shares its space with the
**Editor**, as two tabs; the testbed opens on the Simulation. The scenario's
status, if it reports one, is drawn at its top left.

The column on the right holds, from the top:

- **Controls**, which run the testbed itself: pause and single step, the
  simulation settings below, and a reminder of the keys.
- **Tests**, every scenario by category. Clicking one opens it.
- **Test UI**, the scenario's own panel, whose first line names the
  scenario: ``Test: Drop``. It holds the controls the scenario declares,
  after the **Reset** and **Reset View** buttons every scenario has. A
  scenario that failed to build shows the traceback here instead.
- **Performance**: how long the last step and the last frame's drawing took
  -- current, smoothed and the most since the scenario opened, in ms -- then
  Box2D's own timing of the step and its four slowest stages, and its
  counters of bodies, shapes, contacts, joints and memory.

The **Console** runs along the bottom.

The panels dock, so any of them can be dragged elsewhere or into a tab of
another.

The **Scenario** menu starts a new scenario, opens the source of the running
one in the editor, saves, and shows the directory your scenarios are kept in.
The **Draw** menu turns each of Box2D's debug-draw layers on and off --
shapes, joints, contacts and their normals and impulses, AABBs, centres of
mass, islands and more -- and the most used of them are also checkboxes along
the status bar at the bottom of the window.

The status bar's right end shows the view, as its centre and zoom. Its
**Copy** button copies the view as the two lines a scenario declares to open
there, ``camera_center`` and ``camera_zoom``: frame a scenario by hand, then
paste.

The simulation settings
-----------------------

The Controls panel's settings apply to whichever scenario is running, and
stay as they are when another is opened.

.. list-table::
   :widths: 20 80

   * - Threads
     - How many threads the world steps on, 1 to 32; 4 to start with. A
       change takes effect at the next step, by opening the scenario again
       in a new world with that many threads -- its controls back at their
       defaults, and the view reframed. A build without threads, such as
       the browser's, shows "Threads: 1" instead.
   * - Substeps
     - The substeps of each step, 1 to 32; 20 to start with. More is more
       accurate and slower. A change applies from the next step.
   * - Hertz
     - Steps per second, 10 to 240; 60 to start with. Each step advances the
       world by 1/Hertz of a second, and the testbed steps as many times a
       second as that, so the scene keeps to real time either way: a lower
       Hertz is coarser steps, not slow motion.
   * - Max speed
     - The world's ``max_linear_speed``, in m/s.
   * - Recycle dist
     - The world's ``contact_recycle_distance``, in m.
   * - Continuous Collision, Sleep, Warm starting
     - The world's ``enable_continuous``, ``enable_sleeping`` and
       ``enable_warm_starting``.

Max speed, Recycle dist and the three checkboxes are set on the running
world from the next step, and every world the testbed makes afterwards starts
with them.

Keys
----

Each of these does what one of the panels' buttons does, so a scenario can be
driven without the mouse:

.. list-table::
   :widths: 20 80

   * - ``P``
     - Pause and resume: the play and pause button in Controls.
   * - ``O``
     - Single step: the step button in Controls, which pauses first, so it
       advances one step.
   * - ``R``
     - Reset the scenario: its Reset button.
   * - ``Home``
     - Reset the view: its Reset View button.
   * - ``[`` ``]``
     - Open the previous or next scenario in the Tests panel, wrapping round
       at the ends.

A scenario can take keys of its own, which its docstring lists; the
Scenario menu's **Edit the running one** opens it. The testbed's keys and a
scenario's work while the Simulation tab is showing, wherever the pointer is,
and not while the Editor tab is in front of it. Nor do they while the editor,
the console or another text field has the keyboard, so typing ``pr`` into the
console does not pause the simulation and restart the scenario.

The mouse
---------

Over the Simulation view:

- **left-drag** on a dynamic body pulls it, with a mouse joint from the
  point you pressed to the pointer. Every scenario gets this without writing
  anything, though one can replace it with its own mouse handling;
- **middle-drag** pans the view;
- the **wheel** zooms, towards or away from the view's centre.

Reset
-----

**Reset**, or ``R``, throws the scenario's world away and builds the scene
again in a new world, made with the Controls panel's settings as they are
then. The scenario's controls and the view stay as they were.

A new world, rather than the old one emptied, because that is what makes the
scene the one first built, step for step: a reset scene runs exactly as it did
the first time, unless it was built from Python's random numbers, which come
out differently each time. A few of the shipped scenarios are, such as
Rounded's pile of random polygons, and come back different on each reset.

**Reset View**, or ``Home``, frames the scenario the way opening it does:
at the view it declares, or, if it declares none, around what can move in it
now. Reset does not, so a scene can be reset over and over in the view you
have set up.
