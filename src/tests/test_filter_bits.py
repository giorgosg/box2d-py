# tests/test_filter_bits.py
"""Collision categories and masks are Box2D's 64 bits, defaults included.

CollisionFilter's default mask used to be 0xFFFF, so a world query made
without a filter skipped every shape whose category bits were all above the
low sixteen, and a shape given ``CollisionFilter()`` would not touch one. Box2D's
own defaults -- b2DefaultFilter and b2DefaultQueryFilter -- have every mask bit
set, and so do these now.
"""

import pytest

from box2d import CollisionCategoryRegistry, CollisionFilter, ShapeProxy
from box2d._box2d import lib

#: Box2D's mask fields are uint64_t.
EVERY_BIT = (1 << 64) - 1

#: A category bit no 16-bit mask covers.
HIGH = 1 << 40
TOP = 1 << 63


# --- the defaults are Box2D's -----------------------------------------------


def test_all_is_every_bit():
    assert CollisionFilter.ALL == EVERY_BIT


def test_default_filter_is_box2d_s():
    ours = CollisionFilter().b2Filter[0]
    theirs = lib.b2DefaultFilter()
    assert (ours.categoryBits, ours.maskBits, ours.groupIndex) == (
        theirs.categoryBits,
        theirs.maskBits,
        theirs.groupIndex,
    )


def test_default_query_filter_is_box2d_s():
    ours = CollisionFilter().b2QueryFilter[0]
    theirs = lib.b2DefaultQueryFilter()
    assert (ours.categoryBits, ours.maskBits) == (
        theirs.categoryBits,
        theirs.maskBits,
    )


def test_blocking_a_category_keeps_the_high_bits():
    blocked = CollisionFilter().block_collision_with(0x2)
    assert blocked.mask == EVERY_BIT & ~0x2
    assert blocked.b2Filter.maskBits == EVERY_BIT & ~0x2


# --- default queries find shapes in high categories --------------------------


@pytest.fixture
def high(world):
    """A static box at the origin whose only category is bit 40."""
    body = world.add_body(position=(0, 0))
    body.add_box(2, 2, filter=CollisionFilter(category=HIGH))
    return body.shapes[0]


def test_shape_keeps_a_high_category(high):
    assert high.filter.category == HIGH
    assert high.filter.mask == EVERY_BIT
    high.filter = CollisionFilter(category=TOP, mask=TOP)
    assert (high.filter.category, high.filter.mask) == (TOP, TOP)


def test_query_aabb_finds_a_high_category_by_default(world, high):
    from box2d import AABB

    assert world.query_aabb(AABB((-1, -1), (1, 1))) == [high]


def test_query_circle_finds_a_high_category_by_default(world, high):
    assert world.query_circle((0, 0), 0.5) == [high]


def test_query_shape_finds_a_high_category_by_default(world, high):
    assert world.query_shape(ShapeProxy.box(1, 1)) == [high]


@pytest.mark.parametrize("first_hit_only", [False, True])
def test_cast_ray_finds_a_high_category_by_default(world, high, first_hit_only):
    hits = world.cast_ray((-5, 0), (10, 0), first_hit_only=first_hit_only)
    assert [hit.shape for hit in hits] == [high]
    assert hits[0].point.x == pytest.approx(-1.0)


def test_cast_shape_finds_a_high_category_by_default(world, high):
    hits = world.cast_shape(ShapeProxy.circle(0.25, (-5, 0)), (10, 0))
    assert [hit.shape for hit in hits] == [high]


def test_cast_mover_stops_at_a_high_category_by_default(world, high):
    assert world.cast_mover((-5, -0.5), (-5, 0.5), 0.25, (10, 0)) < 1.0


def test_collide_mover_finds_a_high_category_by_default(world, high):
    planes = world.collide_mover((-1.1, -0.5), (-1.1, 0.5), 0.25)
    assert [plane.shape for plane in planes] == [high]


def test_a_query_filter_can_still_leave_a_high_category_out(world, high):
    assert world.query_circle((0, 0), 0.5, filter=CollisionFilter(mask=0xFFFF)) == []


# --- shape filters --------------------------------------------------------


def _resting_height(world, ground_filter, box_filter):
    ground = world.add_body(position=(0, 0))
    ground.add_box(20, 1, filter=ground_filter)
    box = world.add_body(body_type="dynamic", position=(0, 2))
    box.add_box(1, 1, filter=box_filter)
    for _ in range(120):
        world.step(1 / 60, 4)
    return box.position.y


def test_a_default_filter_collides_with_a_high_category(world):
    """CollisionFilter() on the ground, bit 40 on the box: the box lands."""
    height = _resting_height(world, CollisionFilter(), CollisionFilter(category=HIGH))
    assert height == pytest.approx(1.0, abs=0.05)


def test_a_mask_without_the_bit_lets_a_high_category_through(world):
    height = _resting_height(
        world, CollisionFilter(mask=0xFFFF), CollisionFilter(category=HIGH)
    )
    assert height < 0.0, "the box should fall through the ground"


# --- a registry names every bit -----------------------------------------------


def test_registry_names_all_64_bits():
    registry = CollisionCategoryRegistry()
    bits = [registry.define(f"c{i}") for i in range(64)]
    assert bits == [1 << i for i in range(64)]
    assert CollisionFilter(category="c63", registry=registry).category == TOP
    with pytest.raises(ValueError, match="64"):
        registry.define("one too many")
