"""What the Benchmark scenarios do, where a crash test cannot see it.

test_testbed.py and test_testbed_ui.py drive every scenario and every
control, but only check that nothing raises. A drum that boxes escape from,
or a heap that starts outside its ring, passes both.

These scenes are big, so the tests use the smaller ends of the controls
where they can.
"""

from box2d_testbed import tb_benchmark  # noqa: F401  (registers the scenarios)
from testbed_scenarios import dynamic_bodies, run, scenario


def test_the_tumbler_holds_its_boxes_without_crushing_them_together(world):
    test = scenario(world, "Benchmark", "Tumbler")

    # The feed takes a box a step, so all 400 are in within 7 s.
    run(test, 10.0)

    boxes = dynamic_bodies(world)
    assert len(boxes) == test.max_bodies
    # The boxes are 0.25 m squares, so two whose middles are under 0.15 m
    # apart overlap by 10 cm or more, whatever their angles. A drum too small
    # for them packs them into each other and into its walls.
    centres = [box.position for box in boxes]
    crushed = sum(
        1
        for i, a in enumerate(centres)
        for b in centres[i + 1 :]
        if (a - b).length < 0.15
    )
    assert crushed == 0, f"{crushed} pairs of boxes overlap"
