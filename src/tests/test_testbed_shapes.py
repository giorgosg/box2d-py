"""What the Shapes scenarios do, where a crash test cannot see it.

test_testbed.py and test_testbed_ui.py drive every scenario and every
control, but only check that nothing raises. A control that runs cleanly and
does nothing passes both, which is how the Conveyor Belt's speed slider left
boxes that had come to rest sitting still on a running belt.
"""

import pytest

from box2d import World
from box2d_testbed import tb_shapes  # noqa: F401  (registers the scenarios)
from box2d_testbed.base_test import BaseTest

HERTZ = 60


@pytest.fixture
def world():
    world = World()
    yield world
    world.destroy()


def scenario(world, name):
    test = BaseTest.registry["Shapes"][name](world)
    test.setup()
    return test


def run(test, seconds):
    for _ in range(int(seconds * HERTZ)):
        test.world.step(1 / HERTZ, 4)
        test.after_step(1 / HERTZ)


def dynamic_bodies(world):
    return [body for body in world.bodies if body.type == "dynamic"]


def test_starting_the_conveyor_belt_moves_boxes_resting_on_it(world):
    test = scenario(world, "Conveyor Belt")
    test.tangent_speed = 0.0
    run(test, 3.0)
    boxes = dynamic_bodies(world)
    assert not any(box.awake for box in boxes), "boxes on a still belt fall asleep"
    before = [box.position.x for box in boxes]

    test.tangent_speed = 3.0
    run(test, 1.0)

    # Carried right at up to 3 m/s; it takes them a moment to get going.
    moved = [box.position.x - x for box, x in zip(boxes, before)]
    assert all(distance > 1.5 for distance in moved), moved
