# tests/test_wind.py
"""Shape.apply_wind pushes a shape with moving air.

b2Shape_ApplyWind was unbound. It belongs on the shape rather than the body
because how much force the wind delivers depends on how much of that shape it
can see, so a broadside plank catches more than an edge-on one.
"""

import pytest

from box2d import Vec2, World


@pytest.fixture
def world():
    world = World()
    world.gravity = (0, 0)  # so only the wind moves anything
    yield world
    world.destroy()


def blow(world, shapes, wind=(10, 0), steps=120, **kwargs):
    for _ in range(steps):
        for shape in shapes:
            shape.apply_wind(wind, **kwargs)
        world.step(1 / 60, 4)


def test_wind_moves_a_shape(world):
    body = world.add_body(body_type="dynamic", position=(0, 0))
    shape = body.add_box(0.2, 4, density=1.0)

    blow(world, [shape])

    assert body.position.x > 1.0, "the wind should have pushed it downwind"


def test_no_wind_moves_nothing(world):
    body = world.add_body(body_type="dynamic", position=(0, 0))
    shape = body.add_box(0.2, 4, density=1.0)

    blow(world, [shape], wind=(0, 0))

    assert body.position.x == pytest.approx(0.0, abs=1e-3)


def test_projected_area_matters(world):
    """The point of applying wind per shape rather than per body."""
    broadside_body = world.add_body(body_type="dynamic", position=(0, 0))
    broadside = broadside_body.add_box(4, 0.1, density=1.0)

    edge_on_body = world.add_body(body_type="dynamic", position=(0, 20))
    edge_on = edge_on_body.add_box(0.1, 4, density=1.0)

    blow(world, [broadside, edge_on], wind=(0, 10))

    broadside_moved = broadside_body.position.y
    edge_on_moved = edge_on_body.position.y - 20
    assert broadside_moved > edge_on_moved, "the broad face should catch more"


def test_wind_direction_is_followed(world):
    body = world.add_body(body_type="dynamic", position=(0, 0))
    shape = body.add_circle(radius=0.5, density=1.0)

    blow(world, [shape], wind=(-10, 0))

    assert body.position.x < -1.0


def test_drag_one_settles_at_wind_speed(world):
    """Box2D uses wind - drag * shape_velocity, so drag=1 is the physical case."""
    body = world.add_body(body_type="dynamic", position=(0, 0))
    shape = body.add_box(0.2, 4, density=1.0)

    blow(world, [shape], wind=(10, 0), drag=1.0, steps=240)

    assert body.linear_velocity.x == pytest.approx(10.0, abs=0.5)


def test_lower_drag_overshoots_the_wind(world):
    """drag scales how much of its own motion the wind notices, not the force.

    Below 1 the wind keeps seeing a stationary shape, so it accelerates past
    wind speed instead of settling at it. This is worth pinning because Box2D's
    own header calls drag "the force that opposes the relative velocity", which
    reads like a force multiplier and predicts the opposite.
    """
    speeds = {}
    for drag in (1.0, 0.5, 0.1):
        body = world.add_body(body_type="dynamic", position=(0, 40 * drag))
        shape = body.add_box(0.2, 4, density=1.0)
        for _ in range(120):
            shape.apply_wind((10, 0), drag=drag)
            world.step(1 / 60, 4)
        speeds[drag] = body.linear_velocity.x

    assert speeds[1.0] < speeds[0.5] < speeds[0.1]
    assert speeds[1.0] == pytest.approx(10.0, abs=1.0), "drag=1 tracks the wind"
    assert speeds[0.1] > 50.0, "low drag runs away"


def test_wind_is_vector_like(world):
    body = world.add_body(body_type="dynamic", position=(0, 0))
    shape = body.add_circle(radius=0.5)

    for wind in ((1, 0), [1, 0], Vec2(1, 0)):
        shape.apply_wind(wind)
    world.step(1 / 60, 4)


def test_wind_wakes_a_sleeping_body(world):
    world.gravity = (0, -10)
    ground = world.add_body(position=(0, -1))
    ground.add_box(20, 1)
    body = world.add_body(body_type="dynamic", position=(0, 0))
    shape = body.add_box(1, 1, density=1.0)

    for _ in range(400):
        world.step(1 / 60, 4)
    assert body.awake is False, "the body should have settled and slept"

    shape.apply_wind((50, 0), drag=1.0, wake=True)
    assert body.awake is True


def test_wind_can_leave_a_sleeping_body_alone(world):
    world.gravity = (0, -10)
    ground = world.add_body(position=(0, -1))
    ground.add_box(20, 1)
    body = world.add_body(body_type="dynamic", position=(0, 0))
    shape = body.add_box(1, 1, density=1.0)

    for _ in range(400):
        world.step(1 / 60, 4)
    assert body.awake is False

    shape.apply_wind((50, 0), drag=1.0, wake=False)
    assert body.awake is False
