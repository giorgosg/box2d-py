"""What the Shapes scenarios do, where a crash test cannot see it.

test_testbed.py and test_testbed_ui.py drive every scenario and every
control, but only check that nothing raises. A control that runs cleanly and
does nothing passes both, which is how the Conveyor Belt's speed slider left
boxes that had come to rest sitting still on a running belt.
"""

import pytest

from box2d import Polygon, PolygonDef
from box2d_testbed import tb_shapes  # noqa: F401  (registers the scenarios)
from testbed_scenarios import run, scenario


def dynamic_bodies(world):
    return [body for body in world.bodies if body.type == "dynamic"]


def test_starting_the_conveyor_belt_moves_boxes_resting_on_it(world):
    test = scenario(world, "Shapes", "Conveyor Belt")
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


def test_icing_the_middle_stretch_lets_a_box_resting_there_slide(world):
    test = scenario(world, "Shapes", "Chain Materials")
    # Grippy enough to stop the box on the middle stretch's gentle slope.
    test.icy_friction = 1.0
    run(test, 7.0)
    box = test.boxes[0]
    assert not box.awake, "the box should have come to rest"
    resting_at = box.position

    test.icy_friction = 0.0
    run(test, 2.0)

    # Frictionless on a 1-in-7 slope, it slides downhill, to the right, at
    # 1.4 m/s^2: 2.8 m in two seconds.
    assert box.position.x > resting_at.x + 2.0


def test_reset_rebuilds_the_platform_with_the_shape_and_scale_chosen(world):
    test = scenario(world, "Shapes", "Modify Geometry")
    test.shape = "polygon"
    test.scale = 2.0
    run(test, 0.5)

    test.reset = (test.reset or 0) + 1

    platform = next(body for body in world.bodies if body.type == "kinematic")
    (shape,) = platform.shapes
    assert isinstance(shape, Polygon), f"the platform is a {type(shape).__name__}"
    # Box2D's sample makes the polygon a box 0.5 by 0.75 from its centre.
    corners = {(round(v.x, 6), round(v.y, 6)) for v in shape.vertices}
    assert corners == {(-1.0, -1.5), (1.0, -1.5), (1.0, 1.5), (-1.0, 1.5)}


@pytest.mark.parametrize(
    "name, top",
    [
        # The boxes start 28 m up, and slide down to the ground.
        ("Friction", 28.5),
        # The bodies drop from 40 m, and the restitution 1 ones come back up.
        ("Restitution", 40.5),
    ],
)
def test_the_opening_view_shows_the_ground_and_the_drop(world, name, top):
    test = scenario(world, "Shapes", name)
    center, zoom = test.view()

    # zoom is half the visible height.
    assert center.y - zoom <= 0.0, "the ground is below the view"
    assert center.y + zoom >= top, "the bodies start above the view"


def test_a_new_platform_shape_keeps_the_geometry_it_was_given(world):
    test = scenario(world, "Shapes", "Modify Geometry")
    square = [(-1, -1), (1, -1), (1, 1), (-1, 1)]

    shape = test.add_shape(PolygonDef(square, radius=0.25))

    assert shape.radius == pytest.approx(0.25), "the rounding was dropped"
