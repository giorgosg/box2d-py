"""
This module defines SurfaceMaterial, Box2D's ``b2SurfaceMaterial``: the
friction, restitution and other properties of a shape's surface.
"""

from dataclasses import dataclass, fields, replace
from typing import Any, Mapping
from ._checked import lib
from .debug_draw import Color

_default_material = lib.b2DefaultSurfaceMaterial()


@dataclass
class SurfaceMaterial:
    """
    The physical properties of a shape's surface, Box2D's ``b2SurfaceMaterial``.

    A shape is made with one, as :class:`.ShapeDef`'s ``material``, and a
    chain with one per segment or one for them all, as :class:`.ChainDef`'s
    ``materials``. The fields and their defaults are Box2D's, in Box2D's
    order, so ``SurfaceMaterial()`` is Box2D's default material.

    A material is plain data. Making a shape copies its values into Box2D, so
    changing a material afterwards does not change shapes already made with
    it: set the shape's ``surface_material`` for that.

    Attributes:
        friction: The Coulomb (dry) friction coefficient, usually in the range
            [0,1]. default=0.6
        restitution: The coefficient of restitution (bounce), usually in the
            range [0,1]. default=0.0
        rolling_resistance: The rolling resistance coefficient, usually in the
            range [0,1]. default=0.0
        tangent_speed: The tangent speed for conveyor belt effects. default=0.0
        user_material: An id of the application's own, which the world's
            friction and restitution mixers are given to tell materials apart.
            default=0
        custom_color: A colour for debug draw, as a 0xRRGGBB int or a
            :class:`.Color`; 0 draws the shape in the default colours.
            default=0

    Example:
        >>> from box2d import SurfaceMaterial
        >>> ice = SurfaceMaterial(friction=0.02, user_material=1)
        >>> ice.restitution, ice.user_material
        (0.0, 1)
    """

    friction: float = _default_material.friction
    restitution: float = _default_material.restitution
    rolling_resistance: float = _default_material.rollingResistance
    tangent_speed: float = _default_material.tangentSpeed
    user_material: int = _default_material.userMaterialId
    custom_color: Color | int = _default_material.customColor

    @classmethod
    def from_b2SurfaceMaterial(cls, material) -> "SurfaceMaterial":
        """Build one from a C struct, as read back out of Box2D."""
        return cls(
            friction=material.friction,
            restitution=material.restitution,
            rolling_resistance=material.rollingResistance,
            tangent_speed=material.tangentSpeed,
            user_material=material.userMaterialId,
            custom_color=material.customColor,
        )

    @property
    def b2SurfaceMaterial(self):
        """
        Creates and returns the C structure for this surface material.

        Returns:
            A b2SurfaceMaterial C structure representing this material
        """
        material = lib.b2DefaultSurfaceMaterial()
        material.friction = self.friction
        material.restitution = self.restitution
        material.rollingResistance = self.rolling_resistance
        material.tangentSpeed = self.tangent_speed
        material.userMaterialId = self.user_material
        material.customColor = (
            self.custom_color.b2HexColor
            if isinstance(self.custom_color, Color)
            else self.custom_color
        )
        return material


#: The SurfaceMaterial fields, which the shape-making calls also take as
#: keywords.
_MATERIAL_FIELDS = tuple(field.name for field in fields(SurfaceMaterial))


def _with_fields(material: SurfaceMaterial, given: Mapping[str, Any]):
    """``material`` with the fields in ``given`` replaced.

    A field given as None is left as the material has it, so a caller can
    pass ``custom_color=colour if colourful else None``. ``material`` itself
    is not changed: a new one is made whenever a field is.
    """
    changes = {name: value for name, value in given.items() if value is not None}
    return replace(material, **changes) if changes else material


def _check_material(material, where):
    """Refuse anything but a SurfaceMaterial, saying what to pass instead.

    A bare int was once taken as the material id, so say where that goes now.
    """
    if not isinstance(material, SurfaceMaterial):
        raise TypeError(
            f"{where} takes a SurfaceMaterial, not {type(material).__name__}; "
            "for a material id, pass SurfaceMaterial(user_material=...) or "
            "the user_material= keyword"
        )
