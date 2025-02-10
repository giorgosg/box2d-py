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
        cls.category, cls.name = category, name

    def __init__(self, world, debug_draw, ui_window):
        self.world = world
        self.debug_draw = debug_draw
        self.ui_window = ui_window
        self.mouse_joint = None  # For default dragging

    def setup(self):
        """
        Set up simulation objects in the Box2D world.
        Override this method in each test subclass.
        """
        raise NotImplementedError("Each test must implement the setup method.")

    def init_ui(self):
        """
        Initialize test-specific UI elements.
        This method is called right after setup() and after the UI window is created,
        allowing you to create additional UI controls (e.g. buttons, sliders) in self.ui_window.
        Override this method in your test subclass if additional UI is required.
        """
        pass

    def update(self, dt):
        """
        Called every frame after the debug draw has rendered the simulation.
        dt: elapsed time since last frame.
        """
        pass

    def on_mouse_down(self, pos):
        """
        Default mouse-down: if a shape is hit, create a mouse joint for dragging.
        pos: world coordinate (Vec2) of the mouse event.
        """
        if self.mouse_joint is not None:
            return
        from box2d.math import AABB

        query_aabb = AABB(
            lower=(pos.x - 0.1, pos.y - 0.1), upper=(pos.x + 0.1, pos.y + 0.1)
        )
        shapes = self.world.query_aabb(query_aabb)
        for shape in shapes:
            body = shape.body
            if body.type == "dynamic":
                self.mouse_joint = self.world.add_mouse_joint(
                    body, (pos.x, pos.y), max_force=1000.0, damping_ratio=0.7
                )
                break

    def on_mouse_drag(self, pos, rel):
        """
        Default mouse-drag: update the target position of the active mouse joint.
        pos: current world coordinate (Vec2)
        rel: delta movement.
        """
        if self.mouse_joint is not None:
            self.mouse_joint.target = (pos.x, pos.y)

    def on_mouse_release(self, pos):
        """
        Default mouse-release: destroy the active mouse joint.
        pos: world coordinate (Vec2) at release.
        """
        if self.mouse_joint is not None:
            self.mouse_joint.destroy()
            self.mouse_joint = None

    def cleanup(self):
        """
        Called when the test is finished.
        """
        pass


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
