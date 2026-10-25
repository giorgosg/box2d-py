The testbed in a browser
========================

The testbed also runs in a web page. CPython, Box2D and these bindings are
compiled to WebAssembly and run under `Pyodide <https://pyodide.org/>`_, and
the same testbed draws through imgui into a canvas: the same scenarios,
panels, editor and console as on the desktop, with nothing to install.

The first visit downloads about 15 MB -- the Pyodide runtime, and the imgui
and numpy packages built for it -- which the browser then keeps, so later
visits start sooner. The page reports its progress while it loads, and any
error that stops it.

What is different
-----------------

- **One thread.** A browser runs this build of Box2D without threads, so the
  Controls panel shows "Threads: 1 (this build has no threads)" in place of
  the slider, and ``box2d.HAS_THREADS`` is False at the console.
- **The imgui renderer.** There is no OpenGL for the testbed to use in the
  page, so the world is drawn through imgui's own drawing instead.
- **An older imgui.** The page gets imgui from Pyodide's own packages, which
  are a little behind the desktop's. The testbed works on both, but a few
  editor niceties may be missing in the page; the console's Tab, for one,
  completes the name at the end of the prompt, wherever the cursor is.
- **Files in memory.** The editor works as on the desktop -- New, Fork, Save
  and Run all do what :doc:`scenarios` describes -- but your scenario
  directory is in memory, so what you write there lasts until the page is
  reloaded or closed. Sharing a scenario, below, is how to keep it, and how to
  pass it on.

Sharing a scenario
------------------

The page adds **Share** and **Open link** to the editor's toolbar, for the
sharing server it is served from, and **Copy link** once something has been
shared.

**Share** uploads what is in the editor, saved or not, and copies its link.
**Copy link** copies the last link again. A link is the full SHA-256 hash of
the scenario's source, so the same source always gets the same link. Every
shared scenario is public to anyone with its link, cannot be changed or
deleted once shared, and can be up to 64 KiB.

**Open link** asks for a link, or the hash on its own, and opens that
scenario in the editor, read-only and without running it. It is then in the
editor's drop-down for the rest of the visit, as ``shared/`` followed by its
hash. From there:

- **Run** runs it, as Run runs a file of your own: its scenario is registered
  and put on screen.
- **Fork** copies it into your directory as an editable file, named
  ``shared_`` and the first twelve characters of its hash, then ``_copy``, and
  runs the copy, as forking anything does.

Only links from the server the page came from are accepted.

Opening a shared scenario safely
--------------------------------

A shared scenario is Python, written by whoever shared it, and running it
runs that code in your page, able to do whatever the page can. So the testbed
never runs it on arrival. Opening a link downloads the source and shows it,
read-only, with a note that it has not been run; nothing in it runs until you
press **Run** or **Fork**. Read it first.

What is downloaded is checked against the link: the testbed hashes the source
it receives, and refuses it unless the hash matches. So a link always opens
exactly the source it was made from, whatever server or cache it passed
through.

Building and serving it
-----------------------

The browser build is made from a clone of the project, with Pyodide's
cross-compiler. `web/README.md
<https://github.com/giorgosg/box2d-py/blob/main/web/README.md>`_ covers
building the WebAssembly wheel and serving the page, and `server/README.md
<https://github.com/giorgosg/box2d-py/blob/main/server/README.md>`_ the
sharing server, which serves the page too. A page served without the sharing
server runs as described here, but has nowhere to share to.

The desktop testbed hides Share and Open link, since its scenarios are files
already. The project's `CONTRIBUTING.md
<https://github.com/giorgosg/box2d-py/blob/main/CONTRIBUTING.md>`_ says how
to turn them on there, against a sharing server of your own.
