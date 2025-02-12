"""
Tests for the CollisionFilter module.

This file:
  - Runs the module's doctests.
  - Verifies the string representation.
  - Tests chaining methods (e.g. add/remove, allow/block).
  - Verifies operator overloading for union (|) and collision testing (&).
  - Exercises group filtering (positive vs. negative groups).
  - Checks conversion to the underlying C structure.
  - Covers a complex scenario combining multiple filters.
"""

import pytest
import doctest

from box2d.collision_filter import (
    CollisionFilter,
    filters_collide,
    CollisionCategoryRegistry,
)


def test_collision_filter_docstrings():
    """Run the doctests defined in the collision_filter module."""
    import box2d.collision_filter as cf

    results = doctest.testmod(cf)
    assert results.failed == 0, "Doctests failed in the collision_filter module."


def test_collision_filter_repr():
    """Ensure that the __repr__ output contains expected information."""
    reg = CollisionCategoryRegistry(auto_create=True)
    cf_obj = CollisionFilter(category="cat1", mask="cat2", group=3, registry=reg)
    rep = repr(cf_obj)
    assert rep.startswith("CollisionFilter(")
    assert "group=3" in rep
    assert "0x" in rep  # Categories and masks are shown in hexadecimal format


def test_add_remove_category():
    """Test add_category and remove_category methods, including warning on removal of an unset category."""
    reg = CollisionCategoryRegistry(auto_create=True)
    cf_obj = CollisionFilter(category="base", registry=reg)
    base_bit = reg.get("base")
    assert cf_obj.category == base_bit

    # Add a new category "added"
    cf_obj.add_category("added")
    added_bit = reg.get("added")
    expected_category = base_bit | added_bit
    assert cf_obj.category == expected_category

    # Remove an existing category "base"
    cf_obj.remove_category("base")
    assert cf_obj.category == added_bit

    # Removing a category that is not set should emit a warning.
    with pytest.warns(
        UserWarning, match="Category 'nonexistent' is not set; cannot remove it."
    ):
        cf_obj.remove_category("nonexistent")


def test_allow_block_collision():
    """Test allow_collision_with and block_collision_with methods to modify the mask."""
    reg = CollisionCategoryRegistry(auto_create=True)
    cf_obj = CollisionFilter(category="player", registry=reg)
    initial_mask = CollisionFilter.ALL
    assert cf_obj.mask == initial_mask

    # Allow collision with "enemy" (mask remains unchanged if ALL was used)
    cf_obj.allow_collision_with("enemy")
    assert cf_obj.mask == initial_mask

    # Block collision with "enemy" removes its bit from the mask.
    enemy_bit = reg.get("enemy")
    cf_obj.block_collision_with("enemy")
    expected_mask = initial_mask & ~enemy_bit
    assert cf_obj.mask == expected_mask

    # Test chaining: allow "obstacle" then block "player"
    cf_obj.allow_collision_with("obstacle").block_collision_with("player")
    obstacle_bit = reg.get("obstacle")
    player_bit = reg.get("player")
    expected_mask = (expected_mask | obstacle_bit) & ~player_bit
    assert cf_obj.mask == expected_mask


def test_or_operator():
    """Test that the bitwise OR operator merges the categories and masks correctly."""
    reg = CollisionCategoryRegistry(auto_create=True)
    cf1 = CollisionFilter(category="cat1", mask="mask1", group=2, registry=reg)
    cf2 = CollisionFilter(category="cat2", mask="mask2", group=2, registry=reg)
    combined = cf1 | cf2

    expected_category = reg.get("cat1") | reg.get("cat2")
    expected_mask = reg.parse("mask1") | reg.parse("mask2")
    # The combined filter should take the group from the left-hand side.
    assert combined.category == expected_category
    assert combined.mask == expected_mask
    assert combined.group == cf1.group


def test_and_operator_standard():
    """Test __and__ to ensure that standard category/mask filtering works."""
    reg = CollisionCategoryRegistry(auto_create=True)
    f_a = CollisionFilter(category="player", mask="enemy", group=0, registry=reg)
    f_b = CollisionFilter(category="enemy", mask="player", group=0, registry=reg)
    # Collision occurs if (f_a.category & f_b.mask) and (f_b.category & f_a.mask) are both nonzero.
    assert (f_a & f_b) is True


def test_and_operator_group_filtering():
    """Test __and__ to check group overriding:
    - Positive group forces collision.
    - Negative group prevents collision.
    - Different groups fall back to standard filtering.
    """
    reg = CollisionCategoryRegistry(auto_create=True)

    # Positive group: should force collision even if category/mask would not normally match.
    f1 = CollisionFilter(category="a", mask="b", group=5, registry=reg)
    f2 = CollisionFilter(category="c", mask="d", group=5, registry=reg)
    assert (f1 & f2) is True, "Positive group should force collision"

    # Negative group: should prevent collision.
    f3 = CollisionFilter(category="a", mask="b", group=-3, registry=reg)
    f4 = CollisionFilter(category="c", mask="d", group=-3, registry=reg)
    assert (f3 & f4) is False, "Negative group should prevent collision"

    # Different groups: revert to standard category/mask filtering.
    f5 = CollisionFilter(category="player", mask="enemy", group=1, registry=reg)
    f6 = CollisionFilter(category="enemy", mask="player", group=2, registry=reg)
    assert (f5 & f6) is True


def test_to_c_filter():
    """Test that to_c_filter creates a C structure with the same category, mask and group values."""
    reg = CollisionCategoryRegistry(auto_create=True)
    f = CollisionFilter(category="foo", mask="bar", group=7, registry=reg)
    c_filter = f.to_c_filter()
    assert c_filter.categoryBits == f.category
    assert c_filter.maskBits == f.mask
    assert c_filter.groupIndex == f.group


def test_chaining_methods():
    """Test chaining multiple method calls together to modify the filter."""
    reg = CollisionCategoryRegistry(auto_create=True)
    # Start with a filter with a base category.
    f = CollisionFilter(category="base", registry=reg)
    # Chain modifications: add categories "a" and "b", allow "enemy", block "base", then set group.
    f.add_category("a", "b").allow_collision_with("enemy").block_collision_with(
        "base"
    ).set_group(10)

    # Expected category: block_collision_with only affects the mask, so the category membership is unchanged.
    expected_category = reg.get("base") | reg.get("a") | reg.get("b")
    assert f.category == expected_category, (
        "block_collision_with should not remove a category from collision membership "
        "as it only modifies the mask."
    )

    # Expected mask: start with ALL, then block "base" removes that bit.
    expected_mask = CollisionFilter.ALL & ~reg.get("base")
    assert f.mask == expected_mask

    # Verify group change.
    assert f.group == 10


def test_complex_combined_filters():
    """Test a more complex scenario by combining multiple filters and verifying collision logic."""
    reg = CollisionCategoryRegistry(auto_create=True)

    # Create filter f1 with multiple modifications.
    f1 = CollisionFilter(category="player", mask="enemy", registry=reg)
    f1.add_category("ally").allow_collision_with("obstacle")

    # Create a second filter f2 with different modifications.
    f2 = CollisionFilter(category="enemy", mask="player", registry=reg)
    f2.add_category("obstacle").block_collision_with("ally")

    # Combine the two filters using the OR operator.
    combined = f1 | f2
    expected_category = (
        reg.get("player") | reg.get("ally") | reg.get("enemy") | reg.get("obstacle")
    )
    assert combined.category == expected_category

    expected_mask = (reg.get("enemy") | reg.get("obstacle")) | reg.get("player")
    assert combined.mask == expected_mask

    # The group is taken from f1.
    assert combined.group == f1.group

    # Test collision explicitly against another filter.
    f3 = CollisionFilter(category="enemy", mask="player", registry=reg)
    # Collision should occur if:
    #   (combined.category & f3.mask) != 0 AND (f3.category & combined.mask) != 0.
    collision_expected = ((combined.category & f3.mask) != 0) and (
        (f3.category & combined.mask) != 0
    )
    assert (combined & f3) == collision_expected
