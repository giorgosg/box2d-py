import functools

from box2d import Vec2
from .testbed_state import state
from .ui import UI, UIProperty


def format_view_declaration(center, zoom) -> str:
    """The camera state as the two lines a scenario would declare.

    The point of showing the camera in the status bar is to frame a scenario
    by hand and then keep that framing, so this produces something to paste
    straight into the class rather than numbers to transcribe.

    Args:
        center: The camera centre, as a Vec2 or any vector-like.
        zoom: Half the visible height, in world units.

    Returns:
        str: e.g. ``"camera_center = (0.75, 0.9)\ncamera_zoom = 4.0"``
    """
    center = Vec2(center)
    return (
        f"camera_center = ({round(center.x, 2)!r}, {round(center.y, 2)!r})\n"
        f"camera_zoom = {round(float(zoom), 2)!r}"
    )


class BaseTest:
    """
    Base class for physics tests.
    Each test subclass must specify a category and a name.
    """

    registry = {}
    reset = UI.button("Reset")
    reset_view = UI.button("Reset View")
    # Both work whatever state the scene is in -- Reset is how a scene whose
    # rebuild failed halfway gets another go.
    reset.always_runs = reset_view.always_runs = True

    #: Where the camera sits when this scenario is opened, as (x, y). Leave
    #: None to frame the scenario's moving parts automatically.
    camera_center = None

    #: Half the visible height, in world units. Smaller is closer in. None
    #: derives it from the scenario's contents.
    camera_zoom = None

    #: Bounds for an automatically derived zoom, so a scenario with an enormous
    #: static ground does not open zoomed all the way out.
    MIN_AUTO_ZOOM = 2.0
    MAX_AUTO_ZOOM = 45.0

    #: True while there is a whole scene: setup has finished, and is not
    #: running again. Otherwise -- before the first setup, while setup or a
    #: rebuild runs, or after a setup that raised -- setting a control only
    #: stores its value, which setup reads, and its callbacks do not run. So a
    #: callback can rely on everything setup creates.
    is_set_up = False

    def __init_subclass__(cls, *, category, name, **kwargs):
        super().__init_subclass__(**kwargs)
        if category not in BaseTest.registry:
            BaseTest.registry[category] = {}
        BaseTest.registry[category][name] = cls
        cls.category, cls.name = category, name

    def __init__(self, world):
        self.world = world
        self.mouse_joint = None  # For default dragging
        self._setup_started = False
        # Whichever setup this scenario ends up with -- its own, a parent's or
        # a mixin's -- is wrapped once, around all of it, so a subclass's
        # super().setup() does not count as the scene being finished.
        self.setup = _tracking_set_up(self, self.setup)
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

    def status(self):
        """What the scenario is doing, shown at the top left of the view.

        Return a string, a list of strings for several lines, or None for
        nothing. Called every frame. Text drawn in debug_draw is placed in the
        world and scrolls with the camera; this stays put.
        """
        return None

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
        if self._held_mouse_joint() is not None:
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
        joint = self._held_mouse_joint()
        if joint is not None:
            joint.target = (pos.x, pos.y)

    def on_mouse_release(self, pos):
        """
        Default mouse-release: destroy the active mouse joint.
        pos: world coordinate (Vec2) at release.
        """
        joint = self._held_mouse_joint()
        if joint is not None:
            joint.destroy()
            self.mouse_joint = None

    def _held_mouse_joint(self):
        """The mouse joint, destroying and dropping it if Box2D took it down.

        Returns the joint while it is live, and None once it has gone.

        A scenario that destroys the body being dragged takes the joint with
        it -- Box2D destroys a body's joints along with the body -- and the
        testbed calls the mouse handlers directly, with no guard, so each one
        checks here rather than using a joint that would raise.
        """
        if self.mouse_joint is not None and not self.mouse_joint.is_valid:
            # Nothing to tidy: the kinematic body the joint pulled from went
            # with it.
            self.mouse_joint = None
        return self.mouse_joint

    def view(self):
        """Where the camera should sit for this scenario, as (center, zoom).

        Declared values win. Otherwise the view is framed around the bodies
        that can actually move, which is nearly always what you want to look
        at: a lot of scenarios sit on ground geometry hundreds of units wide,
        and framing that instead leaves the interesting part a few pixels tall.

        Called once the scenario has been set up, so it can measure what
        setup built.
        """
        center, zoom = self.camera_center, self.camera_zoom
        if center is not None and zoom is not None:
            return Vec2(center), zoom

        bounds = self.moving_bounds()
        if bounds is None:
            # Nothing moves: a query or character scenario. Frame the static
            # geometry instead, which is the whole scene in that case.
            world_bounds = self.world.bounds
            bounds = (
                (world_bounds.lower.x, world_bounds.lower.y),
                (world_bounds.upper.x, world_bounds.upper.y),
            )
            # An empty world reports a degenerate box at the origin rather
            # than an inverted one, so check for no extent instead.
            (lower_x, lower_y), (upper_x, upper_y) = bounds
            if upper_x - lower_x <= 0 and upper_y - lower_y <= 0:
                return Vec2(center or (0.0, 0.0)), zoom or 20.0

        (lower_x, lower_y), (upper_x, upper_y) = bounds
        if center is None:
            center = ((lower_x + upper_x) / 2, (lower_y + upper_y) / 2)
        if zoom is None:
            # Fit the taller of the two axes, allowing for the window being
            # wider than it is tall, and leave a little room around the edge.
            half_height = max((upper_y - lower_y) / 2, (upper_x - lower_x) / 2 / 1.6)
            zoom = min(max(half_height * 1.3, self.MIN_AUTO_ZOOM), self.MAX_AUTO_ZOOM)
        return Vec2(center), zoom

    def moving_bounds(self):
        """The box around every non-static body, or None if there are none.

        Returns:
            tuple: ((lower_x, lower_y), (upper_x, upper_y)), or None.
        """
        points = []
        for body in self.world.bodies:
            if body.type == "static":
                continue
            for shape in body.shapes:
                aabb = shape.aabb
                points.append((aabb.lower.x, aabb.lower.y))
                points.append((aabb.upper.x, aabb.upper.y))
        if not points:
            return None
        xs = [x for x, _ in points]
        ys = [y for _, y in points]
        return (min(xs), min(ys)), (max(xs), max(ys))

    def cleanup(self):
        """
        Called when the test is finished.
        """
        pass

    def apply_view(self):
        """Point the testbed camera at this scenario.

        Called when the scenario is opened, by the Reset View button and by
        the Home key. Reset does not call it, so restarting a scenario keeps
        whatever view you had set up.
        """
        center, zoom = self.view()
        self.app_state.center = (center.x, center.y)
        self.app_state.scale = zoom

    @reset_view.callback
    def on_reset_view(self, key, value):
        """Callback for the Reset View button."""
        self.apply_view()

    def rebuild(self):
        """Throw the scene away and build it again, keeping the controls.

        What Reset does, and what a control that changes how the scene is
        built should call. Destroying the bodies takes their shapes and
        joints with them. Does nothing before the first setup, which will
        build the scene itself; after a setup that raised it tries again.
        """
        if not self._setup_started:
            return
        for body in list(self.world.bodies):
            body.destroy()
        self.mouse_joint = None
        self.setup()

    @reset.callback
    def on_reset(self, key, value):
        """Callback for the Reset button."""
        self.rebuild()

    @classmethod
    def get_first_test(cls):
        """
        Returns an instance of the first registered test.
        """
        for tests in BaseTest.registry.values():
            for test_cls in tests.values():
                return test_cls
        return None

    @classmethod
    def get_all_tests(cls):
        """
        Returns the full test registry.
        """
        return BaseTest.registry


def _tracking_set_up(scenario, setup):
    """Wrap a scenario's setup so the scenario knows when its scene is whole."""

    @functools.wraps(setup)
    def run(*args, **kwargs):
        scenario._setup_started = True
        scenario.is_set_up = False
        result = setup(*args, **kwargs)
        scenario.is_set_up = True
        return result

    return run
