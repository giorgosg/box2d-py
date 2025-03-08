"""
This module provides a CollisionFilter class for managing collision filtering
parameters along with a CollisionCategoryRegistry class that handles the creation
and lookup of named collision categories.

Features:
    - Named category creation via a registry.
    - Methods that accept multiple categories at once.
    - Operator overloading (|) for combining CollisionFilter instances.
    - Introspection support (list_categories) for debugging.
    - Optional auto-creation of categories when unknown strings are encountered.

Example usage:
    >>> # With auto_create enabled, new categories are defined automatically:
    >>> filter_a = CollisionFilter(category="player", mask="enemy", group=0)
    >>> filter_a
    CollisionFilter(category=0x1, mask=0x2, group=0)
"""

import warnings
from ._box2d import lib, ffi


class CollisionCategoryRegistry:
    """
    A registry to manage named collision categories.

    Each category is automatically assigned a unique bit. The valid bits
    run from 0x0001 to 0x8000, which gives up to 16 unique categories.

    By default, auto_create is disabled (False) so that
    category names must be explicitly defined. This prevents typos from
    inadvertently creating new categories. However, the default registry
    below is created with auto_create=True for easier prototyping.
    """

    def __init__(self, auto_create: bool = False):
        self._categories = {}
        self._next_bit = 0x0001  # Start at bit 0x0001
        self.auto_create = auto_create

    def define(self, name: str) -> int:
        """
        Define a new collision category with a unique bit, or return the existing bit
        if already defined.

        Args:
            name: The name of the collision category.

        Returns:
            The bitmask value assigned to this category.

        Raises:
            ValueError if the maximum number of categories (16) is exceeded.

        Example:
            >>> reg = CollisionCategoryRegistry()
            >>> reg.define("player")
            1
            >>> reg.define("player")
            1
        """
        if name in self._categories:
            return self._categories[name]
        if self._next_bit > 0x8000:  # Maximum available bits (16 categories)
            raise ValueError("Maximum number of collision categories reached (16).")
        self._categories[name] = self._next_bit
        self._next_bit <<= 1
        return self._categories[name]

    def get(self, name: str) -> int:
        """
        Get the bitmask for a named category.

        Args:
            name: The name of the collision category.

        Returns:
            The bitmask associated with the category.

        Raises:
            ValueError if the category has not been defined.

        Example:
            >>> reg = CollisionCategoryRegistry(auto_create=True)
            >>> reg.define("player")
            1
            >>> reg.get("player")
            1
        """
        try:
            return self._categories[name]
        except KeyError:
            raise ValueError(f"Category '{name}' is not defined.")

    def parse(self, cat) -> int:
        """
        Convert a category provided as a string (name) or integer into an integer bitmask.
        When auto_create is enabled, automatically define new categories that haven't been defined.

        Args:
            cat: A collision category as a name or a bitmask.

        Returns:
            The corresponding bitmask.

        Example:
            >>> reg = CollisionCategoryRegistry(auto_create=True)
            >>> reg.parse("enemy")
            1
            >>> reg.parse("player")
            2
            >>> reg.parse(4)
            4
        """
        if isinstance(cat, str):
            if cat not in self._categories:
                if self.auto_create:
                    return self.define(cat)
                else:
                    raise ValueError(f"Category '{cat}' is not defined.")
            return self.get(cat)
        return int(cat)

    def list_categories(self) -> dict:
        """
        Return a copy of the defined categories.

        Returns:
            dict: A dictionary mapping category names to their bitmask values.

        Example:
            >>> reg = CollisionCategoryRegistry(auto_create=True)
            >>> reg.define("player")
            1
            >>> reg.list_categories()
            {'player': 1}
        """
        return self._categories.copy()


# A module-level default registry instance with auto_create enabled.
DEFAULT_CATEGORY_REGISTRY = CollisionCategoryRegistry(auto_create=True)


class CollisionFilter:
    """
    A helper class for managing Box2D collision filtering parameters.

    Attributes:
        category (int): Bitmask representing the collision categories that this shape belongs to.
                        It is used in combination with the mask to determine which collisions occur.
        mask (int): Bitmask representing which collision categories this shape is allowed to interact with.
                    When the bitwise AND of one shape's category and another shape's mask is nonzero,
                    a collision is possible (subject to group filtering).
        group (int): Collision group index for this shape.
                     The group overrides normal category/mask filtering:
                       - A value of 0 (the default) means no grouping; collision is determined solely by category and mask.
                       - If both shapes share a nonzero group:
                           • A positive value forces them to always collide.
                           • A negative value forces them to never collide.
                       - If the group values differ (or only one is nonzero), the standard category/mask rules are applied.

    The API is chainable and accepts categories (and masks) as either integers or names (resolved
    via a registry). The group is strictly an integer.

    Examples (Fluent Interface):
        >>> f1 = CollisionFilter("player").allow_collision_with("enemy")
        >>> f2 = CollisionFilter("enemy").allow_collision_with("player")
        >>> f3 = CollisionFilter("ally").allow_collision_with("enemy")
        >>> f1 & f2 # checks if two collision filters would collide
        True
        >>> f1 & f3
        True
        >>> f1 = f1.block_collision_with("ally")
        >>> f1 & f3
        False
    """

    ALL = 0xFFFF  # Default mask (all bits set)
    DEFAULT_CATEGORY = 0x0001  # Default category if none is provided

    def __init__(
        self,
        category: int | str | list[int | str] | tuple[int | str] = DEFAULT_CATEGORY,
        mask: int | str | list[int | str] | tuple[int | str] = ALL,
        group: int = 0,
        registry: "CollisionCategoryRegistry" = None,
    ):
        """
        Initialize a new CollisionFilter.

        Args:
            category (int or str or list): The collision category bitmask, name, or list of names/bitmasks.
                                          If string(s) are provided, they are resolved via the registry.
                                          If a list is provided, all categories are combined with bitwise OR.
            mask (int or str or list): The collision mask bitmask, name, or list of names/bitmasks.
                                      Similarly, string(s) are resolved via the registry.
                                      If a list is provided, all masks are combined with bitwise OR.
            group (int): The collision group index.
                         * 0 indicates no grouping; standard category/mask rules apply.
                         * A nonzero value overrides the usual filtering, as follows:
                              - If both shapes have the same nonzero positive group, they always collide.
                              - If both shapes have the same nonzero negative group, they never collide.
            registry (CollisionCategoryRegistry, optional): The registry used for resolving category names.
                                                              Defaults to the module-level default.

        Returns:
            CollisionFilter: A new instance with the specified filtering parameters.

        Example:
            >>> reg = CollisionCategoryRegistry(auto_create=True)
            >>> filter_a = CollisionFilter(category=0x1, mask=CollisionFilter.ALL, group=0, registry=reg)
            >>> filter_a
            CollisionFilter(category=0x1, mask=0xFFFF, group=0)
            >>> filter_b = CollisionFilter(category=["player", "ally"], mask=["enemy", "projectile"], registry=reg)
            >>> filter_b
            CollisionFilter(category=0x3, mask=0xC, group=0)
        """
        self.registry = registry if registry is not None else DEFAULT_CATEGORY_REGISTRY

        # Handle category (single value or list)
        if isinstance(category, list) or isinstance(category, tuple):
            self.category = 0
            for cat in category:
                self.category |= self.registry.parse(cat)
        else:
            self.category = self.registry.parse(category)

        # Handle mask (single value or list)
        if isinstance(mask, list) or isinstance(mask, tuple):
            self.mask = 0
            for m in mask:
                self.mask |= self.registry.parse(m)
        else:
            self.mask = self.registry.parse(mask)

        self.group = group

    def add_category(self, *cats) -> "CollisionFilter":
        """
        Add one or more collision categories to this filter.

        Args:
            *cats: One or more collision categories (int or str) to be added.

        Returns:
            CollisionFilter: Self, to allow chaining.

        Example:
            >>> reg = CollisionCategoryRegistry(auto_create=True)
            >>> filter_a = CollisionFilter(category="player", registry=reg)
            >>> filter_a.add_category("ally", "powerup")
            CollisionFilter(category=0x7, mask=0xFFFF, group=0)
        """
        for cat in cats:
            self.category |= self.registry.parse(cat)
        return self

    def remove_category(self, *cats) -> "CollisionFilter":
        """
        Remove one or more collision categories from this filter.

        Args:
            *cats: Collision categories (int or str) to remove.

        Returns:
            CollisionFilter: Self, to allow chaining.

        Warnings:
            A warning is emitted if a category that is not set is attempted to be removed.

        Example:
            >>> import warnings
            >>> reg = CollisionCategoryRegistry(auto_create=True)
            >>> filter_a = CollisionFilter(category="player", registry=reg)
            >>> filter_a.remove_category("player")
            CollisionFilter(category=0x0, mask=0xFFFF, group=0)
        """
        for cat in cats:
            bit = self.registry.parse(cat)
            if not (self.category & bit):
                warnings.warn(f"Category '{cat}' is not set; cannot remove it.")
            self.category &= ~bit
        return self

    def allow_collision_with(self, *cats) -> "CollisionFilter":
        """
        Allow collisions with one or more categories by including them in the mask.

        Args:
            *cats: Collision categories (int or str) to allow.

        Returns:
            CollisionFilter: Self, to allow chaining.

        Example:
            >>> reg = CollisionCategoryRegistry(auto_create=True)
            >>> # Start with a filter whose mask is initially 0.
            >>> filter_a = CollisionFilter(category="player", mask=0, registry=reg)
            >>> filter_a.allow_collision_with("enemy")
            CollisionFilter(category=0x1, mask=0x2, group=0)
        """
        for cat in cats:
            self.mask |= self.registry.parse(cat)
        return self

    def block_collision_with(self, *cats) -> "CollisionFilter":
        """
        Block collisions with the specified categories.

        This method updates the filter so that it does not allow collisions with the given categories.
        Unlike `allow_collision_with()`, which adds categories to the list of permitted collisions,
        this method marks the provided categories as blocked. In other words, it prevents interactions
        with those categories regardless of previous settings.

        Args:
            *cats: One or more collision categories (int or str) to block.

        Returns:
            CollisionFilter: Self, to allow chaining.

        Example:
            >>> reg = CollisionCategoryRegistry(auto_create=True)
            >>> filter_a = CollisionFilter(category="player", mask=0xFFFF, registry=reg)
            >>> filter_a.block_collision_with("enemy")
            CollisionFilter(category=0x1, mask=0xFFFD, group=0)
        """
        for cat in cats:
            self.mask &= ~self.registry.parse(cat)
        return self

    def set_group(self, group: int) -> "CollisionFilter":
        """
        Set the collision group index for this filter.

        Args:
            group (int): The collision group index.
                         * 0: No overriding group filtering—the standard category/mask rules apply.
                         * Nonzero: Overrides the default filtering when both shapes share the same group.
                                  - Positive values force an always collide scenario.
                                  - Negative values force a never collide scenario.

        Returns:
            CollisionFilter: Self, to allow chaining.

        Example:
            >>> reg = CollisionCategoryRegistry(auto_create=True)
            >>> filter_a = CollisionFilter(category="player", registry=reg)
            >>> filter_a.set_group(5)
            CollisionFilter(category=0x1, mask=0xFFFF, group=5)
        """
        self.group = group
        return self

    @property
    def b2Filter(self):
        """
        Convert this CollisionFilter into a Box2D b2Filter C structure.

        Returns:
            b2Filter: A newly created b2Filter structure with the appropriate category, mask, and group values.

        Example:
            >>> reg = CollisionCategoryRegistry(auto_create=True)
            >>> c_filter = CollisionFilter(category="player", mask="enemy", group=0, registry=reg).b2Filter
            >>> c_filter.categoryBits == 1
            True
            >>> c_filter.maskBits == 2
            True
            >>> c_filter.groupIndex == 0
            True
        """
        c_filter = ffi.new("b2Filter*")
        c_filter.categoryBits = self.category
        c_filter.maskBits = self.mask
        c_filter.groupIndex = self.group
        return c_filter

    @property
    def b2QueryFilter(self):
        """
        Convert this CollisionFilter into a Box2D b2QueryFilter C structure. The group is not included in the query filter.

        Returns:
            b2QueryFilter: A newly created b2QueryFilter structure with the appropriate category and mask values.

        Example:
            >>> reg = CollisionCategoryRegistry(auto_create=True)
            >>> c_filter = CollisionFilter(category="player", mask="enemy", group=0, registry=reg).b2QueryFilter
            >>> c_filter.categoryBits == 1
            True
            >>> c_filter.maskBits == 2
            True
        """
        c_filter = ffi.new("b2QueryFilter*")
        c_filter.categoryBits = self.category
        c_filter.maskBits = self.mask
        return c_filter

    def __or__(self, other: "CollisionFilter") -> "CollisionFilter":
        """
        Combine two CollisionFilter instances using the bitwise OR operator.

        The new filter will have the combined category and mask values.
        The group is retained from self (left-hand side).

        Args:
            other (CollisionFilter): Another collision filter to combine with.

        Returns:
            CollisionFilter: A new filter with merged properties.

        Example:
            >>> reg = CollisionCategoryRegistry(auto_create=True)
            >>> filter_a = CollisionFilter(category="player", registry=reg)
            >>> filter_b = CollisionFilter(category="powerup", group=5, registry=reg)
            >>> filter_a | filter_b
            CollisionFilter(category=0x3, mask=0xFFFF, group=0)
        """
        return CollisionFilter(
            category=self.category | other.category,
            mask=self.mask | other.mask,
            group=self.group,
            registry=self.registry,
        )

    def __and__(self, other: "CollisionFilter") -> bool:
        """
        Overload the bitwise AND operator to test if two CollisionFilter instances would collide.

        Internally, it applies group filtering first:
             - If both filters share the same nonzero group:
                - A positive group forces collision.
                - A negative group prevents collision.
        Then it checks if:
             - (filter_a.category & filter_b.mask) and (filter_b.category & filter_a.mask)
               are both nonzero.

        Returns:
            bool: True if the filters would result in a collision, False otherwise.

        Example:
            >>> reg = CollisionCategoryRegistry(auto_create=True)
            >>> f1 = CollisionFilter(category="player", mask="enemy", group=0, registry=reg)
            >>> f2 = CollisionFilter(category="enemy", mask="player", group=0, registry=reg)
            >>> f1 & f2
            True
        """
        return filters_collide(self, other)

    def __repr__(self):
        """
        Return a human-readable string representation of this CollisionFilter.

        Returns:
            str: A string in the format:
                 "CollisionFilter(category=0x..., mask=0x..., group=...)" where the category and mask are shown in hexadecimal.

        Example:
            >>> reg = CollisionCategoryRegistry(auto_create=True)
            >>> filter_a = CollisionFilter(category="player", mask="enemy", group=0, registry=reg)
            >>> filter_a
            CollisionFilter(category=0x1, mask=0x2, group=0)
        """
        return (
            f"CollisionFilter(category=0x{self.category:X}, "
            f"mask=0x{self.mask:X}, group={self.group})"
        )


def filters_collide(filter_a: CollisionFilter, filter_b: CollisionFilter) -> bool:
    """
    Determine if two collision filters would allow a collision.

    Collision is determined as follows:
      1. Group filtering:
         If both filters share the same nonzero group:
            - A positive group forces collision.
            - A negative group prevents collision.
      2. Otherwise, collision occurs if:
         (filter_a.category & filter_b.mask) != 0 and (filter_b.category & filter_a.mask) != 0

    Args:
        filter_a (CollisionFilter): The first collision filter.
        filter_b (CollisionFilter): The second collision filter.

    Returns:
        bool: True if the filters would allow a collision, False otherwise.

    Examples:
        >>> reg = CollisionCategoryRegistry(auto_create=True)
        >>> f1 = CollisionFilter(category="player", mask="enemy", group=0, registry=reg)
        >>> f2 = CollisionFilter(category="enemy", mask="player", group=0, registry=reg)
        >>> filters_collide(f1, f2)
        True

        >>> reg = CollisionCategoryRegistry(auto_create=True)
        >>> f3 = CollisionFilter(category="player", mask="enemy", group=3, registry=reg)
        >>> f4 = CollisionFilter(category="enemy", mask="player", group=3, registry=reg)
        >>> filters_collide(f3, f4)
        True

        >>> reg = CollisionCategoryRegistry(auto_create=True)
        >>> f5 = CollisionFilter(category="player", mask="enemy", group=-2, registry=reg)
        >>> f6 = CollisionFilter(category="enemy", mask="player", group=-2, registry=reg)
        >>> filters_collide(f5, f6)
        False
    """
    # Group filtering (overrides standard category/mask rules)
    if filter_a.group == filter_b.group and filter_a.group != 0:
        return (
            filter_a.group > 0
        )  # Positive group indicates always collide; negative indicates never collide.

    # Category/Mask filtering
    collision_a = (filter_a.category & filter_b.mask) != 0
    collision_b = (filter_b.category & filter_a.mask) != 0
    return collision_a and collision_b
