#!/usr/bin/env python
"""Serve the browser testbed locally.

The page needs the wasm wheel on the same origin, so this prepares the newest
one and its build manifest next to index.html before serving the directory.

    python web/serve.py            # then open http://localhost:8000

Build the wheel first if there is not one:

    pyodide build
"""

import argparse
import functools
import http.server
import socketserver
import sys

from prepare import WEB, prepare


class Handler(http.server.SimpleHTTPRequestHandler):
    """Static files, with the headers a Pyodide page wants."""

    def end_headers(self):
        # Nothing here is worth caching between runs of a build.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, format, *args):
        # One line per request, without the date noise.
        sys.stderr.write(f"  {self.requestline}\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    arguments = parser.parse_args()

    destination = prepare()
    wheel = destination
    print(f"serving {wheel.name} ({destination.stat().st_size // 1024} KiB)")

    handler = functools.partial(Handler, directory=str(WEB))
    with socketserver.TCPServer(("", arguments.port), handler) as server:
        print(f"open http://localhost:{arguments.port}  (ctrl-c to stop)\n")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped")


if __name__ == "__main__":
    main()
