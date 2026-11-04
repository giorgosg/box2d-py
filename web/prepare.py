#!/usr/bin/env python3
"""Stage the newest wheels and describe them for the browser bootstrap."""

import json
import pathlib
import shutil

WEB = pathlib.Path(__file__).parent
DIST = WEB.parent / "dist"


def newest_wheel(pattern: str) -> pathlib.Path:
    wheels = sorted(DIST.glob(pattern), key=lambda path: path.stat().st_mtime)
    if not wheels:
        raise SystemExit(
            f"no {pattern} in {DIST}. Build the wheels first with "
            "`src/tools/build_wasm.sh`"
        )
    return wheels[-1]


def stage(wheel: pathlib.Path, stale: str) -> pathlib.Path:
    destination = WEB / wheel.name
    for each in WEB.glob(stale):
        if each != destination:
            each.unlink()
    shutil.copy2(wheel, destination)
    return destination


def prepare() -> pathlib.Path:
    binding = stage(newest_wheel("*wasm32.whl"), "box2d_python-*.whl")
    testbed = stage(newest_wheel("box2d_testbed-*.whl"), "box2d_testbed-*.whl")
    (WEB / "build.json").write_text(
        json.dumps({"wheel": binding.name, "testbed": testbed.name}, indent=2) + "\n",
        encoding="utf-8",
    )
    return binding


if __name__ == "__main__":
    prepared = prepare()
    print(f"prepared {prepared.name} ({prepared.stat().st_size // 1024} KiB)")
