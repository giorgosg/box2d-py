from box2d import Vec2, BodyBuilder
import random, math


@BodyBuilder.extend
def create_random_polygon(self, extent, **kwargs):
    count = 3 + random.randint(0, 5)
    vertices = [
        Vec2(random.uniform(-extent, extent), random.uniform(-extent, extent))
        for _ in range(count)
    ]
    radius = random.uniform(extent / 10, extent / 4)
    try:
        self.polygon(vertices, radius, **kwargs)
    except ValueError:
        self.box(extent, extent, radius, **kwargs)
    return self
