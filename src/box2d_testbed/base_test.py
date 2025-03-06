from box2d import World, Vec2
from .testbed_state import state
from .ui import UI, UIProperty


class BaseTest:
    """
    Base class for physics tests.
    Each test subclass must specify a category and a name.
    """

    registry = {}
    reset = UI.button("Reset")

    def __init_subclass__(cls, *, category, name, **kwargs):
        super().__init_subclass__(**kwargs)
        if category not in BaseTest.registry:
            BaseTest.registry[category] = {}
        BaseTest.registry[category][name] = cls
        cls.category, cls.name = category, name

    def __init__(self, world):
        self.world = world
        self.mouse_joint = None  # For default dragging
        self.app_state = state
        self._ui_values = {}
        for key in dir(self.__class__):
            attr = getattr(self.__class__, key)
            if isinstance(attr, UIProperty):
                # This call will trigger __get__ and store the UIValue in _ui_values.
                getattr(self, key)

    @property
    def ui_elements(self):
        """Return UI elements in declaration order"""
        values = sorted(self._ui_values.items(), key=lambda x: x[1].order)
        return values

    def setup(self):
        """
        Set up simulation objects in the Box2D world.
        Override this method in each test subclass.
        """
        raise NotImplementedError("Each test must implement the setup method.")

    def after_step(self, dt):
        """
        Called after each world step.
        """
        pass

    def debug_draw(self, debug_draw):
        """
        Called every frame after the debug draw has rendered the simulation.
        """
        pass

    def on_key_down(self, key):
        """
        Called when a key is pressed
        """
        pass

    def on_key_up(self, key):
        """
        Called when a key is released
        """
        pass

    def on_mouse_down(self, pos):
        """
        Default mouse-down: if a shape is hit, create a mouse joint for dragging.
        pos: world coordinate (Vec2) of the mouse event.
        """
        if self.mouse_joint is not None:
            return

        shapes = self.world.query_circle(pos, 0.0001)
        for shape in shapes:
            body = shape.body
            if body.type == "dynamic":
                self.mouse_joint = self.world.add_mouse_joint(
                    body,
                    (pos.x, pos.y),
                    max_force=1000.0 * body.mass,
                    damping_ratio=0.7,
                    hertz=5,
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

    @reset.callback
    def on_reset(self, key, value):
        """
        Callback for the reset button.
        Deletes all bodies in the world and runs the test setup again.
        If the test uses parameters (e.g. current_shape), these are preserved.
        """
        for body in list(self.world.bodies):
            body.destroy()
        self.setup()

    @classmethod
    def get_first_test(cls):
        """
        Returns an instance of the first registered test.
        """
        for category, tests in BaseTest.registry.items():
            for name, test_cls in tests.items():
                return test_cls
        return None

    @classmethod
    def get_all_tests(cls):
        """
        Returns the full test registry.
        """
        return BaseTest.registry
