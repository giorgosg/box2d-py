from box2d import World, Vec2
from .testbed_state import state


class UIElement:
    def __init__(
        self,
        control_type,
        key,
        label,
        default=None,
        max_value=None,
        min_value=None,
        options=None,
        callback=None,
        user_data=None,
    ):
        """
        A descriptor for a UI element.

        control_type: The type of control ("button", "label", "combo", "toggle", "int_input").
        key: A unique key for the control.
        label: The display label.
        default: The control's default value.
        max_value: The maximum value (required for int_input)
        min_value: The minimun value (required for int_input)
        options: (Optional) List of options (useful for combo boxes, etc.)
        callback: (Optional) Function to be called when the control changes.
        user_data: (Optional) Additional data to be passed to the callback.
        """
        self.control_type = control_type
        self.key = key
        self.label = label
        self.default = default
        self.max_value = max_value
        self.min_value = min_value
        self.options = options or []
        self.callback = callback
        self.user_data = user_data


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

    def __init__(self, world):
        self.world = world
        self.mouse_joint = None  # For default dragging
        self.app_state = state
        self.ui_elements = [
            UIElement(
                control_type="button",
                key="reset_button",
                label="Reset",
                callback=self.on_reset_click,
            ),
        ]

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

    def on_reset_click(self, key, value):
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
