debug = False


class DebugDrawSettings:
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
        self._keys = (
            "shapes",
            "aabbs",
            "joints",
            "contacts",
            "contact_normals",
            "contact_impulses",
            "friction_impulses",
            "mass",
            "joint_extras",
        )

    def get_current(self):
        """
        returns a list of (key, value, display)
        """
        return [
            (key, self.__getattribute__(key), key.replace("_", " ").capitalize())
            for key in self._keys
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


class TestbedData:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.window_size = (1024, 768)
        self.center = (0, 0)  # Center at origin
        self.scale = 20
        self.gravity = (0, -10)
        self.threads = 4
        self.substeps = 20
        self.hertz = 60
        self.enable_continuous = True
        self.enable_sleep = True
        self.show_dd = DebugDrawSettings()
        self.simulation_paused = False
        self.step_count = 0  # step count for current physics world
        self.step_number = 0  # how many times the step button has been pressed
        self.current_test_cls = None
        self.current_test_obj = None
        self.all_tests = None
        self.perf = PerformanceData()


state = TestbedData()
