#!/usr/bin/env python3
"""Check each wheel in a directory holds its own package and nothing else.

Not a test, as a developer's stale ``build/`` puts old packages in a wheel
without anything being wrong with the checkout: this runs on CI's clean one.
"""

import pathlib
import sys
import zipfile

#: What each distribution's wheel may hold, by the start of its file name.
EXPECTED = {"box2d_python": {"box2d"}, "box2d_testbed": {"box2d_testbed"}}


def main() -> int:
    wheels = sorted(pathlib.Path(sys.argv[1]).glob("*.whl"))
    found = {wheel.name.partition("-")[0] for wheel in wheels}
    if found != set(EXPECTED):
        print(f"expected a wheel each of {sorted(EXPECTED)}, found {sorted(found)}")
        return 1
    failed = False
    for wheel in wheels:
        names = zipfile.ZipFile(wheel).namelist()
        tops = {name.split("/")[0] for name in names}
        packages = {top for top in tops if not top.endswith(".dist-info")}
        wanted = EXPECTED[wheel.name.partition("-")[0]]
        print(f"{wheel.name}: {sorted(packages)}")
        failed = failed or packages != wanted
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
