#!/usr/bin/env python
"""Measure what a frame costs in the testbed, so renderers can be compared.

Run before and after changing how drawing works. It opens the real testbed on
a chosen scenario, runs a set number of frames, and reports the distribution
of per-frame times rather than an average, because a renderer that is usually
quick and occasionally terrible is not the same as a steadily mediocre one
and the mean hides which you have.

    python src/tools/bench_render.py --scenario Benchmark/"Many Pyramids" \
        --set gridcount=10 --frames 400

It also counts the drawing primitives submitted per frame. That number is a
property of the scene rather than the renderer, so it should be identical
across renderers -- if it is not, the two are not being asked to draw the
same thing and the timings mean nothing.
"""

import argparse
import json
import statistics
import sys
import time


def parse_arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario",
        default="Benchmark/Many Pyramids",
        help="Category/Name, e.g. 'Benchmark/Many Pyramids'",
    )
    parser.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="Set a scenario control before measuring; repeatable",
    )
    parser.add_argument("--frames", type=int, default=300, help="Frames to measure")
    parser.add_argument(
        "--warmup",
        type=int,
        default=60,
        help="Frames to discard first, while caches and buffers settle",
    )
    parser.add_argument(
        "--no-sleep",
        action="store_true",
        help="Keep bodies awake, so physics cost is measured rather than skipped",
    )
    parser.add_argument("--json", help="Also write the results here, as JSON")
    parser.add_argument("--label", default="", help="A note stored with the results")
    return parser.parse_args(argv)


def apply_setting(test, assignment):
    """Apply one NAME=VALUE to a scenario, guessing the type from its control."""
    name, _, raw = assignment.partition("=")
    element = dict(test.ui_elements).get(name)
    if element is None:
        raise SystemExit(f"scenario has no control named {name!r}")
    if element.type == "int":
        value = int(raw)
    elif element.type == "float":
        value = float(raw)
    elif element.type == "bool":
        value = raw.lower() in ("1", "true", "yes", "on")
    else:
        value = raw
    setattr(test, name, value)


def counting_renderer(debug_draw, counters):
    """Wrap a debug draw so every primitive it is asked for is counted."""
    primitives = (
        "draw_polygon",
        "draw_solid_polygon",
        "draw_circle",
        "draw_solid_circle",
        "draw_solid_capsule",
        "draw_segment",
        "draw_point",
        "draw_string",
        "draw_bounds",
        "draw_transform",
    )
    for name in primitives:
        original = getattr(debug_draw, name)

        def wrapper(*args, _original=original, _name=name, **kwargs):
            counters[_name] = counters.get(_name, 0) + 1
            return _original(*args, **kwargs)

        setattr(debug_draw, name, wrapper)


def summarise(samples):
    """Median, 95th percentile and worst, in milliseconds."""
    if not samples:
        return {"median": 0.0, "p95": 0.0, "max": 0.0}
    ordered = sorted(samples)
    return {
        "median": statistics.median(ordered),
        "p95": ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))],
        "max": ordered[-1],
    }


def main(argv=None):
    arguments = parse_arguments(argv)

    from box2d_testbed.base_test import BaseTest
    from box2d_testbed.testbed_state import state
    import box2d_testbed.testbed as testbed_module

    category, _, name = arguments.scenario.partition("/")
    registry = BaseTest.registry
    if category not in registry or name not in registry[category]:
        raise SystemExit(f"no such scenario: {arguments.scenario!r}")

    app = testbed_module.TestbedApp()
    runner = app.runner_params

    physics_samples = []
    draw_samples = []
    frame_samples = []
    primitive_counts = {}
    frames = {"count": 0, "last": None}
    total = arguments.warmup + arguments.frames

    previous_post_init = runner.callbacks.post_init

    def post_init():
        if previous_post_init is not None:
            previous_post_init()
        # The simulation picks the first registered scenario as it is built,
        # so the choice has to be made after that rather than before.
        state.current_test_cls = registry[category][name]
        state.enable_sleep = not arguments.no_sleep
        app.simulation.init_test()

        # Controls exist only once the scenario does. Setting one fires its
        # callback, which is what rebuilds the scene at the new size.
        for assignment in arguments.set:
            apply_setting(state.current_test_obj, assignment)

        counting_renderer(app.simulation.debug_draw, primitive_counts)

    previous_pre_frame = runner.callbacks.pre_new_frame

    def pre_new_frame():
        if previous_pre_frame is not None:
            previous_pre_frame()
        frames["count"] += 1
        now = time.perf_counter()

        if frames["count"] > arguments.warmup:
            physics_samples.append(state.perf.physics_ms)
            draw_samples.append(state.perf.draw_ms)
            if frames["last"] is not None:
                frame_samples.append((now - frames["last"]) * 1000.0)
        elif frames["count"] == arguments.warmup:
            # Discard what the warm-up counted.
            primitive_counts.clear()

        frames["last"] = now
        if frames["count"] >= total:
            runner.app_shall_exit = True

    runner.callbacks.post_init = post_init
    runner.callbacks.pre_new_frame = pre_new_frame
    app.run()

    measured = max(1, frames["count"] - arguments.warmup)
    counters = state.perf.counters
    results = {
        "label": arguments.label,
        "scenario": arguments.scenario,
        "settings": arguments.set,
        "frames": measured,
        "bodies": counters.body_count if counters else None,
        "shapes": counters.shape_count if counters else None,
        # A settled scene sleeps, and a sleeping body costs nothing to step --
        # so physics_ms near zero means the pile has come to rest, not that
        # stepping is free. Pass --no-sleep to measure it working.
        "awake": state.perf.awake,
        "physics_ms": summarise(physics_samples),
        "draw_ms": summarise(draw_samples),
        "frame_ms": summarise(frame_samples),
        "primitives_per_frame": {
            key: round(value / measured, 1)
            for key, value in sorted(primitive_counts.items())
            if value
        },
    }

    print(
        f"\n{arguments.scenario}  {' '.join(arguments.set)}"
        f"{'  [' + arguments.label + ']' if arguments.label else ''}"
    )
    print(
        f"  {results['bodies']} bodies ({results['awake']} awake), "
        f"{results['shapes']} shapes, {measured} frames measured\n"
    )
    print(f"  {'':10} {'median':>9} {'p95':>9} {'max':>9}")
    for key in ("physics_ms", "draw_ms", "frame_ms"):
        row = results[key]
        print(f"  {key:10} {row['median']:9.2f} {row['p95']:9.2f} {row['max']:9.2f}")
    print("\n  primitives per frame:")
    for key, value in results["primitives_per_frame"].items():
        print(f"    {key:20} {value:9.1f}")

    if arguments.json:
        with open(arguments.json, "w") as handle:
            json.dump(results, handle, indent=2)
        print(f"\n  written to {arguments.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
