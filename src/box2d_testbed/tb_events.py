from box2d import World, Vec2, CollisionFilter
from .base_test import BaseTest, UI


class FootSensor(BaseTest, category="Events", name="Foot Sensor"):
    def setup(self):
        ground = self.world.new_body().static()
        chain_points = [Vec2(x, 0) for x in range(10, -11, -1)]
        ground.chain(
            chain_points,
            loop=False,
            collision_filter=CollisionFilter(
                category="ground", mask=["foot", "player"]
            ),
        )
        ground = ground.build()

        player = self.world.new_body().dynamic().fixed_rotation().position(0, 2)
        player = player.capsule(
            (0, -0.5),
            (0, 0.5),
            0.5,
            collision_filter=CollisionFilter(category="player", mask=["ground"]),
        )
        player = player.box(
            1,
            0.5,
            offset=(0, -1),
            collision_filter=CollisionFilter(category="foot", mask=["ground"]),
            is_sensor=True,
        )
        self.player = player.build()
        self.overlap_count = 0
        self.move = 0

    def on_key_down(self, key):
        if key == "a":
            self.move = -1
        elif key == "d":
            self.move = 1

    def on_key_up(self, key):
        if key in ("a", "d"):
            self.move = 0

    def after_step(self, dt):
        self.player.apply_force(self.move * Vec2(50, 0), (0, 0), True)
        sensorevents = self.world.get_sensor_events()
        self.overlap_count += len(sensorevents.begin) - len(sensorevents.end)

    def debug_draw(self, debug_draw):
        debug_draw.draw_string((5, 15), f"Overlap count: {self.overlap_count}")
