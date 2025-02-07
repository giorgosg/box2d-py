from box2d import World, Vec2

class BaseTest:
    """
    Base class for physics tests.
    Each test subclass must specify a category and a name.
    """
    registry = {}

    def __init_subclass__(cls, *, category, name, **kwargs):
        super().__init_subclass__(**kwargs)
        if category not in BaseTest.registry:
            BaseTest.registry[category] = {}
        BaseTest.registry[category][name] = cls

    def setup(self, world):
        """
        Set up simulation objects in the Box2D world.
        Override this method in each test subclass.
        """
        raise NotImplementedError("Each test must implement the setup method.")


def get_first_test():
    """
    Returns an instance of the first registered test.
    """
    for category, tests in BaseTest.registry.items():
        for name, test_cls in tests.items():
            return test_cls
    return None


class DefaultTest(BaseTest, category="Examples", name="Default Test"):
    def setup(self, world):
        # Create a wide ground body
        world.new_body().static().position(0, -10).box(50, 10).build()
        
        # Add dynamic bodies
        world.new_body().dynamic().position(-5, 20).box(1, 1).build()
        world.new_body().dynamic().position(5, 30).circle(1).build()
        
        # Add vertical capsule
        world.new_body().dynamic().position(0, 10).capsule(
            (0, 0),  # Local start point
            (0, 2),  # Local end point
            0.5      # Radius
        ).build()
        
        # Add horizontal capsule
        world.new_body().dynamic().position(-3, 15).capsule(
            (-1, 0),  # Local start point
            (1, 0),   # Local end point
            0.3       # Radius
        ).build()