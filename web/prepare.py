#!/usr/bin/env python3
"""Stage the newest WASM wheel and describe it for the browser bootstrap."""

import json
import pathlib
import shutil

WEB = pathlib.Path(__file__).parent
DIST = WEB.parent / "dist"


def newest_wheel() -> pathlib.Path:
    wheels = sorted(DIST.glob("*wasm32.whl"), key=lambda path: path.stat().st_mtime)
    if not wheels:
        raise SystemExit(
            f"no wasm wheel in {DIST}. Build one first with `pyodide build` or "
            "`src/tools/build_wasm.sh`"
        )
    return wheels[-1]


def prepare() -> pathlib.Path:
    wheel = newest_wheel()
    destination = WEB / wheel.name
    for stale in WEB.glob("box2d_python-*wasm32.whl"):
        if stale != destination:
            stale.unlink()
    shutil.copy2(wheel, destination)
    (WEB / "build.json").write_text(
        json.dumps({"wheel": wheel.name}, indent=2) + "\n", encoding="utf-8"
    )
    return destination


if __name__ == "__main__":
    prepared = prepare()
    print(f"prepared {prepared.name} ({prepared.stat().st_size // 1024} KiB)")
