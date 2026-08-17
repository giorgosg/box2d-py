"""
Where the time and the memory went.

Box2D measures itself while it steps. :class:`Profile` is the timing
breakdown of the last step, and :class:`Counters` is the size of the
simulation behind it -- how many bodies, contacts and islands, and how many
bytes they occupy.

Both are snapshots of the step that just finished, so read them after
:meth:`.World.step` and before the next one::

    world.step(1 / 60, 4)
    profile = world.profile
    print(f"{profile.step:.2f}ms, {profile.collide:.2f}ms colliding")

Timings are milliseconds. They come from Box2D's own timer and include only
what Box2D did, so they will not add up to the wall time of your frame.
"""

from dataclasses import dataclass, fields
from typing import List


@dataclass
class Profile:
    """Milliseconds spent in each phase of the last step.

    ``step`` is the total; the rest are phases within it, and they overlap in
    the sense that some are sub-phases of others (``constraints`` is part of
    ``solve``), so summing them is not meaningful. Compare them to each other
    across frames instead, to see which phase grows.
    """

    step: float = 0.0
    pairs: float = 0.0
    collide: float = 0.0
    solve: float = 0.0
    solver_setup: float = 0.0
    constraints: float = 0.0
    prepare_constraints: float = 0.0
    integrate_velocities: float = 0.0
    warm_start: float = 0.0
    solve_impulses: float = 0.0
    integrate_positions: float = 0.0
    relax_impulses: float = 0.0
    apply_restitution: float = 0.0
    store_impulses: float = 0.0
    split_islands: float = 0.0
    transforms: float = 0.0
    sensor_hits: float = 0.0
    joint_events: float = 0.0
    hit_events: float = 0.0
    refit: float = 0.0
    bullets: float = 0.0
    sleep_islands: float = 0.0
    sensors: float = 0.0

    @classmethod
    def from_b2Profile(cls, profile):
        return cls(
            **{name: getattr(profile, c_name) for name, c_name in _PROFILE_FIELDS}
        )

    def slowest(self, count: int = 5) -> List[tuple]:
        """The phases that took longest, as ``(name, milliseconds)`` pairs.

        Excludes ``step``, which is the total and so always the largest.
        """
        timings = [
            (field.name, getattr(self, field.name))
            for field in fields(self)
            if field.name != "step"
        ]
        timings.sort(key=lambda pair: pair[1], reverse=True)
        return timings[:count]


@dataclass
class Counters:
    """How big the simulation is, as of the last step.

    Attributes:
        byte_count: Total bytes Box2D has allocated for this world.
        body_count: Bodies in the world, awake or not.
        shape_count: Shapes across all bodies.
        contact_count: Contacts, including ones not yet touching.
        joint_count: Joints in the world.
        island_count: Islands, i.e. groups of bodies solved together.
        stack_used: Peak bytes of Box2D's per-step stack allocator.
        static_tree_height: Height of the static broad-phase tree.
        tree_height: Height of the moving broad-phase tree. A tree much taller
            than log2(proxy count) is unbalanced and slow to query.
        task_count: Tasks the step was split into, which is how the work was
            spread across workers.
        color_counts: Contacts per solver graph colour. Constraints in one
            colour are solved in parallel, so an even spread parallelises well
            and everything landing in one colour does not.
        awake_contact_count: Contacts the collide pass actually touched.
        recycled_contact_count: Contacts reused rather than rebuilt this step.
    """

    byte_count: int = 0
    body_count: int = 0
    shape_count: int = 0
    contact_count: int = 0
    joint_count: int = 0
    island_count: int = 0
    stack_used: int = 0
    static_tree_height: int = 0
    tree_height: int = 0
    task_count: int = 0
    color_counts: List[int] = None
    awake_contact_count: int = 0
    recycled_contact_count: int = 0

    @classmethod
    def from_b2Counters(cls, counters):
        values = {name: getattr(counters, c_name) for name, c_name in _COUNTER_FIELDS}
        values["color_counts"] = list(counters.colorCounts)
        return cls(**values)


def _camel(name):
    head, *rest = name.split("_")
    return head + "".join(part.title() for part in rest)


# Field names differ only by case convention, so the mapping is derived rather
# than written out twice and left to drift. test_diagnostics checks every
# derived name against the struct.
_PROFILE_FIELDS = [(field.name, _camel(field.name)) for field in fields(Profile)]
_COUNTER_FIELDS = [
    (field.name, _camel(field.name))
    for field in fields(Counters)
    if field.name != "color_counts"
]
