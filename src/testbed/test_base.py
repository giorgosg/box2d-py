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

def get_all_tests():
    """
    Returns the full test registry.
    """
    return BaseTest.registry

