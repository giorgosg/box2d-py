#!/usr/bin/env python3
"""Hold the WebAssembly wheel to a first-visit budget.

Both numbers are what a browser user waits for on a first visit, whatever the
page is. The build runs this in two halves, because the import has to be timed
inside Pyodide and the wheel is only on the machine that built it:

    python wasm_budget.py import OUT.json     # inside Pyodide
    python wasm_budget.py check DIR OUT.json  # on the host; fails over budget

A budget is there to catch a large regression, not to hold a line to the byte:
the import is timed on whichever CI machine turned up, so it has room to spare.
Raise one on purpose, in the change that earns it.
"""

import json
import os
import pathlib
import sys
import time

#: The wheel, to download. It is 305 KiB now.
WHEEL_KIB = 400
#: ``import box2d``, once Pyodide is up. It takes 0.4 s on a fast machine.
IMPORT_SECONDS = 3.0


def measure_import(out: pathlib.Path) -> None:
    start = time.perf_counter()
    import box2d  # noqa: F401

    seconds = time.perf_counter() - start
    out.write_text(json.dumps({"seconds": seconds}))
    print(f"import box2d took {seconds:.2f} s")


def check(wheels: pathlib.Path, measured: pathlib.Path) -> int:
    (wheel,) = wheels.glob("*wasm32.whl")
    kib = wheel.stat().st_size / 1024
    seconds = json.loads(measured.read_text())["seconds"]
    over = kib > WHEEL_KIB or seconds > IMPORT_SECONDS
    report = (
        "| WebAssembly wheel | Now | Budget |\n"
        "| --- | ---: | ---: |\n"
        f"| `{wheel.name}` | {kib:.0f} KiB | {WHEEL_KIB} KiB |\n"
        f"| `import box2d` | {seconds:.2f} s | {IMPORT_SECONDS:.2f} s |\n"
    )
    print(report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as file:
            file.write(report)
    return 1 if over else 0


def main() -> int:
    command, *paths = sys.argv[1:]
    if command == "import":
        measure_import(pathlib.Path(paths[0]))
        return 0
    return check(pathlib.Path(paths[0]), pathlib.Path(paths[1]))


if __name__ == "__main__":
    sys.exit(main())
