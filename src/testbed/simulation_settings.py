debug = False


class SimulationControler:
    """
    A central hub that maintains simulation settings and orchestrates
    interactions between various subsystems of the testbed.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Directly assign to __dict__ here so __setattr__ is bypassed during initialization.
        self.__dict__["_settings"] = {
            # Initialization and simulation parameters.
            "width": 1024,
            "height": 768,
            "center": (
                0,
                0,
            ),  # physics world point that should be at the center of the canvas
            "scale": 30,  # pixels per meter (initial zoom)
            "gravity": (0, -10),
            "hertz": 60,
            "substeps": 4,
            "threads": 4,
            "enable_continuous": True,
            "enable_sleep": True,
            # Debug draw settings (DebugDraw instance should initialize them with default Box2D values):
            "draw_shapes": True,
            "draw_aabbs": False,
            "draw_joints": True,
            "draw_contacts": False,
            "draw_contact_normals": False,
            "draw_contact_impulses": False,
            "draw_friction_impulses": False,
            "draw_mass": False,
            "draw_joint_extras": False,
            # Simulation
            "simulation_paused": False,
            "step_count": 0,  # Step count for the current physics World
            "step_number": 0,  # How many times the step button has been pressed.
            "current_test": None,
            "current_test_obj": None,
            "all_tests": None,
            "physics_ms": 0,
            "physics_ms_avg": 0,
            "debug_draw_ms": 0,
            "debug_draw_ms_avg": 0,
        }
        # Manage observers for individual keys and for all settings.
        self.__dict__["_global_observers"] = []
        self.__dict__["_observers"] = {}

    def subscribe(self, callback, *keys):
        """
        Subscribe a callback to setting changes.
        If key is None then the callback is notified on any setting change.
        Callback signature: callback(key, new_value)
        """
        if not keys:
            self._global_observers.append(callback)
        else:
            for key in keys:
                if key not in self.__dict__["_settings"]:
                    print(f"invalid subscription to {key}")

                self._observers.setdefault(key, []).append(callback)

    def unsubscribe(self, callback, key=None):
        """Unsubscribe a callback for a given key or globally if key is None."""
        print(f"unsubscribing {key}: {callback}")
        if key is None:
            if callback in self._global_observers:
                self._global_observers.remove(callback)
        else:
            if key in self._observers and callback in self._observers[key]:
                self._observers[key].remove(callback)

    def notify(self, key, value):
        """
        Notify all subscribers about the change to a particular setting.
        """
        for callback in self._observers.get(key, []):
            if debug:
                print("calling: ", callback, key, value)
            callback(key, value)
        for callback in self._global_observers:
            if debug:
                print("calling: ", callback, key, value)
            callback(key, value)

    def set(self, key, value):
        """
        Updates a setting and notifies observers if the value changes.
        """
        if key not in self._settings or self._settings[key] != value:
            self._settings[key] = value
        self.notify(key, value)

    def get(self, key):
        """Retrieves a setting value."""
        return self._settings.get(key)

    def update(self, **kwargs):
        """
        Bulk update settings. Observers will be notified for each changed key.
        """
        for key, value in kwargs.items():
            self.set(key, value)

    # --- Attribute access as properties ---
    def __getattr__(self, name):
        """
        Provides property-like access to settings. Called only if the attribute
        isn't found in the usual places.
        """
        _settings = self.__dict__.get("_settings", {})
        if name in _settings:
            return _settings[name]
        raise AttributeError(
            f"{self.__class__.__name__} object has no attribute '{name}'"
        )

    def __setattr__(self, name, value):
        """
        Intercepts attribute assignments. If the name is in the settings,
        delegates setting via the set() method (to trigger notifications).
        Otherwise, assigns as normal.
        """
        if name in ("_settings", "_global_observers", "_observers"):
            # Allow direct setting of internal attributes.
            super().__setattr__(name, value)
        elif name in self._settings:
            self.set(name, value)
        else:
            print(f"New settings parameter: {name}, {value}")
            super().__setattr__(name, value)

    # Also support dictionary-style access:
    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        self.set(key, value)

    def __repr__(self):
        return f"SimulationSettings({self._settings})"


# Globally available singleton instance.
settings = SimulationControler()
