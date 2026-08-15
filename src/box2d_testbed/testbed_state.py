class DebugDrawSettings:
    """Which of Box2D's debug-draw flags are on.

    Every key here must have a matching ``draw_<key>`` property on DebugDraw;
    DebugDrawGL.update_settings raises if one goes missing rather than
    silently leaving a dead toggle in the menu.
    """

    # Shown as checkboxes along the status bar. The rest are menu-only, since
    # fifteen checkboxes do not fit on one row.
    PRIMARY = (
        "shapes",
        "aabbs",
        "joints",
        "contacts",
        "contact_normals",
        "contact_impulses",
        "mass",
    )

    # Where capitalising the key does not read well.
    LABELS = {
        "aabbs": "AABBs",
        "anchor_a": "Anchor A",
        "graph_colors": "Graph colours",
    }

    def __init__(self):
        self.shapes = True
        self.aabbs = False
        self.joints = True
        self.contacts = False
        self.contact_normals = False
        self.contact_impulses = False
        self.friction_impulses = False
        self.mass = False
        self.joint_extras = False
        # Added once the remaining six b2DebugDraw flags were bound.
        self.contact_features = False
        self.islands = False
        self.graph_colors = False
        self.body_names = False
        self.chain_normals = False
        self.anchor_a = False
        self._keys = (
            "shapes",
            "aabbs",
            "joints",
            "joint_extras",
            "contacts",
            "contact_normals",
            "contact_impulses",
            "friction_impulses",
            "contact_features",
            "mass",
            "islands",
            "graph_colors",
            "body_names",
            "chain_normals",
            "anchor_a",
        )

    def get_current(self, primary_only: bool = False):
        """Returns a list of (key, value, display).

        Args:
            primary_only: Limit to the flags worth a permanent checkbox.
        """
        keys = self.PRIMARY if primary_only else self._keys
        return [
            (
                key,
                getattr(self, key),
                self.LABELS.get(key, key.replace("_", " ").capitalize()),
            )
            for key in keys
        ]


class PerformanceData:
    def __init__(self):
        self.physics_ms = 0
        self.physics_ms_avg = 0
        self.physics_ms_max = 0
        self.draw_ms = 0
        self.draw_ms_avg = 0
        self.draw_ms_max = 0
        self.smoothing_avg = 0.9
        # Box2D's own view of the last step, which is narrower than the
        # wall-clock physics_ms measured around it: the gap between them is
        # the binding's overhead.
        self.profile = None
        self.counters = None
        self.awake = 0


class TestbedData:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.center = (0, 0)  # Center at origin
        self.scale = 20
        self.gravity = (0, -10)
        self.threads = 4
        self.substeps = 20
        self.hertz = 60
        self.enable_continuous = True
        self.enable_sleep = True
        # Bound on World for a while, but reachable only from code until now.
        self.enable_warm_starting = True
        self.enable_speculative = True
        self.maximum_linear_speed = 400.0
        self.contact_recycle_distance = 0.05
        self.show_dd = DebugDrawSettings()
        self.simulation_paused = False
        self.step_count = 0  # step count for current physics world
        self.step_number = 0  # how many times the step button has been pressed
        self.current_test_cls = None
        self.current_test_obj = None
        self.all_tests = None
        self.perf = PerformanceData()


state = TestbedData()
