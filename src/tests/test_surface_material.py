"""A shape's surface comes from its SurfaceMaterial, as in Box2D.

``ShapeDef.material`` is Box2D's ``b2ShapeDef.material``, and is where a
shape's friction, restitution, rolling resistance, tangent speed, material id
and debug colour come from. The shape-making calls also take each of those as
a keyword, which fills that field of the material: given with ``material=``,
the keyword wins for its own field, and the caller's material is left as it
was.

ShapeDef used to carry the fields flat beside ``material``, whose values were
then ignored: a shape made with ``material=SurfaceMaterial(friction=0.1)`` got
Box2D's default friction.
"""

import dataclasses

import pytest

from box2d import Color, ShapeDef, SurfaceMaterial
from box2d._box2d import lib
from box2d.shape import Chain

#: A material none of whose fields is Box2D's default, in values a 32-bit
#: float holds exactly, so what Box2D reads back compares equal.
ODD = SurfaceMaterial(
    friction=0.25,
    restitution=0.5,
    rolling_resistance=0.125,
    tangent_speed=1.5,
    user_material=7,
    custom_color=0x00FF00,
)

#: Each way to make a shape, by kind, given the material keywords.
MAKERS = {
    "circle": lambda body, **kw: body.add_circle(0.5, **kw),
    "box": lambda body, **kw: body.add_box(1, 1, **kw),
    "capsule": lambda body, **kw: body.add_capsule((0, 0), (1, 0), 0.25, **kw),
    "polygon": lambda body, **kw: body.add_polygon([(0, 0), (1, 0), (0, 1)], **kw),
    "segment": lambda body, **kw: body.add_segment((0, 0), (1, 0), **kw),
}


@pytest.fixture
def body(world):
    return world.new_body().dynamic().build()


# --- SurfaceMaterial ---------------------------------------------------------


def test_a_material_left_to_its_defaults_is_box2d_s():
    box2d = lib.b2DefaultSurfaceMaterial()
    assert SurfaceMaterial() == SurfaceMaterial.from_b2SurfaceMaterial(box2d)
    assert SurfaceMaterial().user_material == 0


def test_a_material_s_fields_are_box2d_s_in_box2d_s_order():
    """friction first, so ``SurfaceMaterial(0.2)`` reads as it does in C."""
    names = [field.name for field in dataclasses.fields(SurfaceMaterial)]
    assert names == [
        "friction",
        "restitution",
        "rolling_resistance",
        "tangent_speed",
        "user_material",
        "custom_color",
    ]


def test_a_material_reaches_its_struct_whole():
    c = ODD.b2SurfaceMaterial
    assert (c.friction, c.restitution, c.rollingResistance, c.tangentSpeed) == (
        0.25,
        0.5,
        0.125,
        1.5,
    )
    assert (c.userMaterialId, c.customColor) == (7, 0x00FF00)


def test_a_material_takes_a_color_for_its_custom_color():
    material = SurfaceMaterial(custom_color=Color(0, 255, 0))
    assert material.b2SurfaceMaterial.customColor == 0x00FF00


def test_materials_have_no_registry():
    """Each material is plain data: nothing numbers them or keeps them."""
    assert not hasattr(SurfaceMaterial, "get_by_id")
    assert not hasattr(SurfaceMaterial, "clear_registry")
    assert SurfaceMaterial().user_material == SurfaceMaterial().user_material == 0


# --- ShapeDef ----------------------------------------------------------------


def test_a_shape_definition_holds_its_surface_in_its_material():
    names = {field.name for field in dataclasses.fields(ShapeDef)}
    assert "material" in names
    assert not names & {
        "friction",
        "restitution",
        "rolling_resistance",
        "tangent_speed",
        "custom_color",
    }


def test_each_shape_definition_has_a_material_of_its_own():
    first, second = ShapeDef(), ShapeDef()
    assert first.material == SurfaceMaterial()
    assert first.material is not second.material


def test_a_shape_definition_s_material_reaches_its_struct():
    c = ShapeDef(material=ODD).b2ShapeDef.material
    assert SurfaceMaterial.from_b2SurfaceMaterial(c) == ODD


def test_a_shape_definition_refuses_a_bare_material_id():
    with pytest.raises(TypeError, match="user_material"):
        ShapeDef(material=3)


# --- making a shape ----------------------------------------------------------


@pytest.mark.parametrize("kind", MAKERS)
def test_a_shape_made_with_a_material_has_its_values(body, kind):
    shape = MAKERS[kind](body, material=ODD)
    assert shape.surface_material == ODD
    assert shape.friction == 0.25
    assert shape.user_material == 7


@pytest.mark.parametrize("kind", MAKERS)
def test_a_shape_made_with_material_keywords_has_them(body, kind):
    fields = dataclasses.asdict(ODD)
    shape = MAKERS[kind](body, **fields)
    assert shape.surface_material == ODD


def test_a_keyword_overrides_that_field_of_the_material(body):
    shape = body.add_box(1, 1, material=ODD, friction=0.75, user_material=9)
    assert shape.surface_material == dataclasses.replace(
        ODD, friction=0.75, user_material=9
    )


def test_a_keyword_leaves_the_caller_s_material_as_it_was(body):
    material = SurfaceMaterial(friction=0.25)
    body.add_box(1, 1, material=material, friction=0.75)
    assert material == SurfaceMaterial(friction=0.25)


def test_a_keyword_given_as_none_leaves_the_field_alone(body):
    """So a caller can pass ``custom_color=colour if colourful else None``."""
    shape = body.add_circle(0.5, material=ODD, custom_color=None, friction=None)
    assert shape.surface_material == ODD


def test_the_builder_takes_a_material_and_keywords(world):
    built = world.new_body().dynamic().box(1, 1, material=ODD, restitution=0.75).build()
    assert built.shapes[0].surface_material == dataclasses.replace(
        ODD, restitution=0.75
    )


def test_a_shape_made_with_a_colour_keyword_draws_in_it(body):
    shape = body.add_circle(0.5, custom_color=Color(0, 0, 255))
    assert shape.surface_material.custom_color == 0x0000FF


# --- a shape's material, once made -------------------------------------------


def test_setting_a_shape_s_material_sets_every_field(body):
    shape = body.add_circle(0.5)
    shape.surface_material = ODD
    assert shape.surface_material == ODD


def test_a_shape_s_user_material_takes_a_material_s_id(body):
    shape = body.add_circle(0.5, friction=0.75)
    shape.user_material = ODD
    assert shape.user_material == 7
    assert shape.friction == 0.75  # only the id is taken


def test_a_shape_s_user_material_takes_an_int(body):
    shape = body.add_circle(0.5)
    shape.user_material = 42
    assert shape.user_material == 42


# --- chains ------------------------------------------------------------------


@pytest.fixture
def ground(world):
    return world.new_body().static().build()


POINTS = [(0, 0), (1, 0), (2, 0)]


def test_a_chain_made_with_a_material_has_its_values(ground):
    chain = ground.add_chain(POINTS, materials=[ODD])
    for index in range(len(chain.segments)):
        assert chain.get_surface_material(index) == ODD


def test_a_chain_made_with_material_keywords_has_them(ground):
    chain = Chain.create(ground, POINTS, **dataclasses.asdict(ODD))
    assert chain.get_surface_material(0) == ODD


def test_a_chain_keyword_overrides_that_field_of_every_material(ground):
    plain = SurfaceMaterial(friction=0.125)
    materials = [ODD, plain]
    chain = ground.add_chain(POINTS, materials=materials, restitution=0.75)
    assert chain.get_surface_material(0) == dataclasses.replace(ODD, restitution=0.75)
    assert chain.get_surface_material(1) == dataclasses.replace(plain, restitution=0.75)
    assert materials == [ODD, SurfaceMaterial(friction=0.125)]


def test_a_chain_made_with_no_material_settings_has_box2d_s_material(ground):
    chain = ground.add_chain(POINTS)
    box2d = lib.b2DefaultChainDef().materials[0]
    assert chain.get_surface_material(0) == SurfaceMaterial.from_b2SurfaceMaterial(
        box2d
    )
