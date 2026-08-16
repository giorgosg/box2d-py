"""
This module defines the SurfaceMaterial class for managing physical materials in Box2D.
A material defines the friction, restitution, and other properties of a surface.
"""

from dataclasses import dataclass, field
from typing import Optional, ClassVar
from weakref import WeakValueDictionary
from ._box2d import lib, ffi
from .debug_draw import Color


@dataclass
class SurfaceMaterial:
    """
    A material defines the physical properties of a surface in the simulation.

    Materials are used to customize how objects interact when they collide.
    When shapes with different materials collide, Box2D can use custom
    callbacks to determine the resulting friction and restitution.

    Attributes:
        material: User material identifier passed with query results. (auto-generated if not set)
        friction: The Coulomb (dry) friction coefficient, usually in the range [0,1]. default=0.6
        restitution: The coefficient of restitution (bounce), usually in the range [0,1]. default=0.0
        rolling_resistance: The rolling resistance coefficient, usually in the range [0,1]. default=0.0
        tangent_speed: The tangent speed for conveyor belt effects. default=0.0
        custom_color: Custom debug draw color used for visualization.
    """

    # Class variable to track the next available material ID
    _next_material_id: ClassVar[int] = 1

    # Registry to keep track of all created materials by their ID
    # Using WeakValueDictionary so materials can be garbage collected when no longer used
    _materials_registry: ClassVar[WeakValueDictionary] = WeakValueDictionary()

    # Auto-increment material ID by default
    material: int = field(default_factory=lambda: SurfaceMaterial._get_next_id())
    friction: Optional[float] = None
    restitution: Optional[float] = None
    rolling_resistance: Optional[float] = None
    tangent_speed: Optional[float] = None
    custom_color: Optional[Color | int] = None

    @classmethod
    def _get_next_id(cls) -> int:
        """Generate the next unique material ID."""
        material_id = cls._next_material_id
        cls._next_material_id += 1
        return material_id

    def __post_init__(self):
        # Register this material in the registry
        self._materials_registry[self.material] = self

    @classmethod
    def from_b2SurfaceMaterial(cls, material) -> "SurfaceMaterial":
        """Build one from a C struct, as read back out of Box2D.

        The id comes from the struct rather than the auto-increment counter,
        so a material read back keeps the identity it was stored under.
        """
        return cls(
            material=material.userMaterialId,
            friction=material.friction,
            restitution=material.restitution,
            rolling_resistance=material.rollingResistance,
            tangent_speed=material.tangentSpeed,
            custom_color=material.customColor,
        )

    @property
    def b2SurfaceMaterial(self):
        """
        Creates and returns the C structure for this surface material.

        Uses b2DefaultSurfaceMaterial() to get default values and only
        overrides properties that have been explicitly set.

        Returns:
            A b2SurfaceMaterial C structure representing this material
        """
        # Start with defaults
        material = lib.b2DefaultSurfaceMaterial()

        # Always set the material ID, even if using the auto-generated one
        material.userMaterialId = self.material

        # Override with any explicitly set values
        if self.friction is not None:
            material.friction = self.friction
        if self.restitution is not None:
            material.restitution = self.restitution
        if self.rolling_resistance is not None:
            material.rollingResistance = self.rolling_resistance
        if self.tangent_speed is not None:
            material.tangentSpeed = self.tangent_speed
        if self.custom_color is not None:
            if isinstance(self.custom_color, Color):
                material.customColor = self.custom_color.b2HexColor
            else:
                material.customColor = self.custom_color

        return material

    @classmethod
    def default(cls):
        """
        Creates a SurfaceMaterial with Box2D default values.

        Uses b2DefaultSurfaceMaterial() to get the default values from Box2D.

        Returns:
            A SurfaceMaterial instance with default values
        """
        default_mat = lib.b2DefaultSurfaceMaterial()
        return cls(
            material=cls._get_next_id(),  # Still use auto-generated ID
            friction=default_mat.friction,
            restitution=default_mat.restitution,
            rolling_resistance=default_mat.rollingResistance,
            tangent_speed=default_mat.tangentSpeed,
            custom_color=default_mat.customColor,
        )

    @classmethod
    def get_by_id(cls, material_id: int) -> Optional["SurfaceMaterial"]:
        """
        Find a material in the registry by its material ID.

        Args:
            material_id: The material identifier to search for

        Returns:
            The SurfaceMaterial with the specified ID, or None if not found
        """
        return cls._materials_registry.get(material_id)

    @classmethod
    def clear_registry(cls):
        """
        Clear the materials registry.

        This removes all references to materials from the registry but doesn't
        affect any materials still being used by Box2D objects.
        """
        cls._materials_registry.clear()
