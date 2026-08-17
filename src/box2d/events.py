"""
Events reported by the world after a step.

Box2D collects what happened during :meth:`.World.step` and hands it back as
flat arrays. These dataclasses are the Python view of them, with shapes, bodies
and joints resolved back to their wrapper objects rather than left as ids.

All of them describe the step that just finished. Reading does not consume
them, so asking twice between steps gives the same answer, but the next step
replaces them -- read them between steps rather than storing them.

Events are opt-in per shape, and Box2D defaults them off:

- contact begin and end need ``enable_contact_events`` on both shapes
- hit events need ``enable_hit_events``, and only fire above the world's
  :attr:`.World.hit_event_threshold` approach speed
- sensor overlap needs ``enable_sensor_events`` on the visiting shape
"""

from dataclasses import dataclass, field
from typing import List, Optional

from ._box2d import ffi, lib
from .dataclasses import ContactData
from .math import Transform, Vec2


class Contact:
    """A handle on one contact between two shapes, stable across steps.

    Contact events carry one of these, so a contact seen beginning can be
    followed until the matching end event: the identity is Box2D's own contact
    id rather than the pair of shapes, which is what makes it usable as a
    dictionary key.

    The contact may be reclaimed by Box2D at any step, so check
    :attr:`is_valid` before reading :attr:`data`.
    """

    __slots__ = ("_contact_id", "_key")

    def __init__(self, contact_id):
        self._contact_id = contact_id
        # cdata structs are not hashable, so identity travels as a plain tuple.
        self._key = (
            contact_id.index1,
            contact_id.world0,
            contact_id.generation,
        )

    @property
    def is_valid(self) -> bool:
        """Whether Box2D still recognises this contact."""
        return bool(lib.b2Contact_IsValid(self._contact_id))

    @property
    def data(self) -> Optional[ContactData]:
        """The contact's shapes and manifold, or None once it is gone.

        The manifold has no points while the shapes are near but not yet
        touching, which is normal rather than an error.
        """
        if not self.is_valid:
            return None
        return ContactData.from_b2ContactData(lib.b2Contact_GetData(self._contact_id))

    def __eq__(self, other):
        return isinstance(other, Contact) and self._key == other._key

    def __hash__(self):
        return hash(self._key)

    def __repr__(self):
        state = "valid" if self.is_valid else "stale"
        return f"<Contact {self._key} {state}>"


@dataclass
class ContactBeginEvent:
    """Two shapes started touching.

    Attributes:
        shape_a: One of the shapes now touching.
        shape_b: The other shape.
        contact: A handle on this contact, stable until the matching end event.
    """

    shape_a: "Shape"
    shape_b: "Shape"
    contact: Optional[Contact] = None


@dataclass
class ContactEndEvent:
    """Two shapes stopped touching.

    A shape destroyed while touching another produces an end event whose
    shape is already gone, so check :meth:`.Shape.is_valid` before using them.

    Attributes:
        shape_a: One of the shapes that were touching, possibly destroyed.
        shape_b: The other shape, possibly destroyed.
        contact: The contact that ended, matching an earlier begin event.
    """

    shape_a: Optional["Shape"]
    shape_b: Optional["Shape"]
    contact: Optional[Contact] = None


@dataclass
class ContactHitEvent:
    """Two shapes collided hard enough to count as a hit.

    Only reported for shapes with ``enable_hit_events``, and only when the
    approach speed exceeds the world's hit event threshold.

    Attributes:
        shape_a: One of the shapes involved.
        shape_b: The other shape.
        point: Where they hit, in world coordinates.
        normal: The contact normal, pointing from shape_a to shape_b.
        approach_speed: How fast they were closing, in metres per second.
        contact: A handle on the contact this hit belongs to.
    """

    shape_a: "Shape"
    shape_b: "Shape"
    point: Vec2
    normal: Vec2
    approach_speed: float
    contact: Optional[Contact] = None


@dataclass
class ContactEvents:
    """Everything that started, stopped, or hit during the last step."""

    begin: List[ContactBeginEvent] = field(default_factory=list)
    end: List[ContactEndEvent] = field(default_factory=list)
    hit: List[ContactHitEvent] = field(default_factory=list)

    def __bool__(self):
        return bool(self.begin or self.end or self.hit)

    def __len__(self):
        return len(self.begin) + len(self.end) + len(self.hit)


@dataclass
class BodyMoveEvent:
    """A body moved during the last step.

    Box2D reports these only for bodies that actually moved, which makes them a
    cheaper way to update sprites than walking every body each frame.

    Attributes:
        body: The body that moved.
        transform: Its position and rotation after the step.
        fell_asleep: True if the body went to sleep on this step.
    """

    body: "Body"
    transform: Transform
    fell_asleep: bool


@dataclass
class JointEvent:
    """A joint exceeded its force or torque threshold during the last step.

    Thresholds are set per joint definition, via ``force_threshold`` and
    ``torque_threshold``. This is how you detect a joint about to fail, for
    breakable constructions.

    Attributes:
        joint: The joint that reported the event.
    """

    joint: "Joint"
