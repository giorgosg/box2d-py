#!/usr/bin/env python
"""Serve the browser testbed locally.

The page needs the wasm wheel on the same origin, so this copies the newest
one next to index.html and serves the directory.

    python web/serve.py            # then open http://localhost:8000

Build the wheel first if there is not one:

    pyodide build
"""

import argparse
import functools
import http.server
import pathlib
import shutil
import socketserver
import sys

WEB = pathlib.Path(__file__).parent
DIST = WEB.parent / "dist"


class Handler(http.server.SimpleHTTPRequestHandler):
    """Static files, with the headers a Pyodide page wants."""

    def end_headers(self):
        # Nothing here is worth caching between runs of a build.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, format, *args):
        # One line per request, without the date noise.
        sys.stderr.write(f"  {self.requestline}\n")


def newest_wheel():
    wheels = sorted(DIST.glob("*wasm32.whl"), key=lambda p: p.stat().st_mtime)
    if not wheels:
        raise SystemExit(
            f"no wasm wheel in {DIST}. Build one first:\n"
            f"    pyodide build\n"
            f"or run src/tools/build_wasm.sh, which also tests it."
        )
    return wheels[-1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    arguments = parser.parse_args()

    wheel = newest_wheel()
    destination = WEB / wheel.name
    shutil.copy2(wheel, destination)
    print(f"serving {wheel.name} ({destination.stat().st_size // 1024} KiB)")

    # The page hardcodes the wheel name; tell me plainly if they disagree,
    # rather than letting the browser report a 404 for something that is there.
    page = (WEB / "index.html").read_text()
    if wheel.name not in page:
        print(f"\n  WARNING: index.html does not mention {wheel.name}.")
        print("  Update the WHEEL_URL line in web/index.html to match.\n")

    handler = functools.partial(Handler, directory=str(WEB))
    with socketserver.TCPServer(("", arguments.port), handler) as server:
        print(f"open http://localhost:{arguments.port}  (ctrl-c to stop)\n")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped")


if __name__ == "__main__":
    main()
