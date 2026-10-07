"""
A dynamic character controller, built on the mover and pogo joints.

The character is an ordinary dynamic body -- a capsule with its rotation
locked -- so it collides with and pushes everything else in the world, and is
pushed back. Two joints do the moving:

- a mover joint drives it toward the velocity the controller wants, with a
  limited force budget, on x only, so gravity and jumps stay its own;
- a pogo joint, a spring along a ray cast straight down, holds it up off the
  ground. The capsule never touches the floor, which is what lets it ride over
  steps and bumps without catching on them.

The pogo is rebuilt every step wherever the ray lands, so the character can
stand on a moving platform or a swinging bridge as readily as on the ground.

Ported from Box2D's ``samples/dynamic_mover.cpp``. Upstream's advice stands:
copy this into your project and change it to suit your game.

Movement follows the Quake ground and air model, see
https://github.com/id-Software/Quake/blob/master/QW/client/pmove.c#L390,
and the approach is from Tom Waterson's talk,
https://www.youtube.com/watch?v=_jRLlTDqoGI.
"""

import math

from box2d import CollisionFilter, Vec2


class DynamicMover:
    """A capsule character driven by a mover joint and held up by a pogo.

    Call :meth:`update` once per step with the horizontal input, and
    :meth:`jump` when the jump button is pressed.

    The three flags mirror upstream's and drive everything else:

    - ``on_ground``: the ray found ground and the character is not jumping.
      Controls friction, the mover's force budget and the pogo's reach.
    - ``walkable``: the ground under the ray is shallow enough to stand on.
      Controls whether the character can steer at full strength and jump.
    - ``jumping``: a jump is under way, which stops the pogo pulling it back
      down until it is falling onto ground again.
    """

    def __init__(
        self,
        world,
        position,
        capsule=((0.0, -0.5), (0.0, 0.5), 0.3),
        density=1.0,
        filter: CollisionFilter = None,
        enable_pre_solve_events=False,
        jump_speed=7.0,
        max_speed=6.0,
        min_speed=0.1,
        stop_speed=3.0,
        accelerate=20.0,
        air_steer=0.5,
        friction=8.0,
        gravity_scale=1.5,
        max_ground_force=70.0,
        max_air_force=20.0,
        pogo_rest_length=0.9,
        pogo_hertz=5.0,
        pogo_damping_ratio=0.8,
        pogo_compression_scale=100.0,
        pogo_tension_scale=100.0,
        min_ground_normal_y=0.7,
    ):
        self.world = world
        self.jump_speed = jump_speed
        self.max_speed = max_speed
        self.min_speed = min_speed
        self.stop_speed = stop_speed
        self.accelerate = accelerate
        #: Fraction of the ground acceleration available in the air.
        self.air_steer = air_steer
        #: Ground friction, in units of 1/time.
        self.friction = friction
        #: Force the mover joint has for reaching the target velocity. The air
        #: budget is small so the character keeps its momentum while jumping.
        self.max_ground_force = max_ground_force
        self.max_air_force = max_air_force
        self.pogo_rest_length = pogo_rest_length
        self.pogo_hertz = pogo_hertz
        self.pogo_damping_ratio = pogo_damping_ratio
        #: Pogo force limits, as multiples of the character's weight.
        self.pogo_compression_scale = pogo_compression_scale
        self.pogo_tension_scale = pogo_tension_scale
        #: Surfaces steeper than this are not ground.
        self.min_ground_normal_y = min_ground_normal_y

        center1, center2, radius = capsule
        self.center1, self.center2 = Vec2(center1), Vec2(center2)
        self.radius = radius
        self.filter = filter if filter is not None else CollisionFilter()

        self.velocity = Vec2(0, 0)
        self.on_ground = False
        self.walkable = False
        self.jumping = False
        self.jump_ticks = 0

        # The pogo's state, carried across it being rebuilt every step.
        self.pogo_joint = None
        self.pogo_impulse = 0.0
        self.pogo_velocity = 0.0
        self.pogo_length = 0.0

        # The last ground probe, kept for drawing.
        self.cast = None
        self.pogo_origin = Vec2(position) + self.center1
        self.pogo_translation = Vec2(0, -pogo_rest_length)
        self.pogo_fraction = 1.0

        # The mover joint needs something to be relative to. An empty static
        # body of its own, so the character never depends on the scene's.
        self.anchor = world.new_body().static().name("mover anchor").build()
        self.body = (
            world.new_body()
            .dynamic()
            .position(position)
            .gravity_scale(gravity_scale)
            .lock_rotation()
            .enable_sleep(False)
            .name("mover")
            # The joints do all the moving, and surface friction would fight
            # them.
            .capsule(
                self.center1,
                self.center2,
                radius,
                density=density,
                friction=0.0,
                filter=self.filter,
                enable_pre_solve_events=enable_pre_solve_events,
            )
            .build()
        )
        self.mover_joint = world.add_mover_joint(
            self.anchor,
            self.body,
            linear_velocity=(0, 0),
            max_velocity_force=(max_ground_force, 0),
            collide_connected=True,
        )

    @property
    def gravity_scale(self) -> float:
        """How strongly gravity pulls the character. It usually wants to fall
        faster than the rest of the world. The pogo's forces are sized from
        the resulting weight."""
        return self.body.gravity_scale

    @gravity_scale.setter
    def gravity_scale(self, value: float):
        self.body.gravity_scale = value

    @property
    def position(self) -> Vec2:
        return self.body.position

    def destroy(self):
        """Remove the character. Its joints go with its bodies."""
        self.body.destroy()
        self.anchor.destroy()
        self.pogo_joint = None

    def jump(self) -> bool:
        """Jump, if standing on walkable ground. Returns False otherwise."""
        if not self.on_ground or not self.walkable:
            return False

        # Jump relative to the ground, so a rising platform adds to it.
        surface_velocity = 0.0
        ground = self.cast.shape.body if self.cast is not None else None
        if ground is not None and ground.is_valid:
            surface_velocity = ground.get_world_point_velocity(self.cast.point).y

        # Cancel whatever the pogo was doing to the vertical velocity, and add
        # the surface's.
        vy = self.body.linear_velocity.y
        dv = max(0.0, self.jump_speed - vy) + surface_velocity
        self.body.apply_linear_impulse((0, self.body.mass * dv))

        # Stops the pogo stepping down to the ground on the next update.
        self.on_ground = False
        self.walkable = False
        self.jumping = True
        self.jump_ticks = 0
        return True

    def update(self, dt: float, throttle: float):
        """Advance the controller by one step. Throttle is on [-1, 1]."""
        if dt <= 0:
            return

        self._probe_ground()
        self._update_flags()

        self.velocity = self.body.linear_velocity
        self._apply_friction(dt)
        self.mover_joint.max_velocity_force = (self._force_budget(), 0)
        self._accelerate(dt, throttle)
        self._rebuild_pogo()
        self.mover_joint.linear_velocity = self.velocity

    # --- the steps of an update ----------------------------------------------

    def _probe_ground(self):
        """Cast a ray down from the capsule's lower centre."""
        # Reach further while grounded, so the spring can find the ground
        # again on the far side of a step down.
        step_down = self.pogo_rest_length
        reach = self.pogo_rest_length + (step_down if self.on_ground else 0.0)
        self.pogo_origin = self.body.position + self.center1
        self.pogo_translation = Vec2(0, -reach)

        hits = self.world.ray_cast(
            self.pogo_origin,
            self.pogo_translation,
            filter=self.filter,
            first_hit_only=True,
        )
        self.cast = hits[0] if hits else None
        self.pogo_fraction = self.cast.fraction if self.cast else 1.0

    def _update_flags(self):
        if self.jumping:
            self.jump_ticks += 1
            # The ticks give a jump time to leave the ground; otherwise it
            # would end at once, still over the ground it started from.
            if (
                self.jump_ticks > 2
                and self.cast is not None
                and self.velocity.dot(self.cast.normal) <= 0
            ):
                self.jumping = False

        if self.cast is not None:
            # The ray can still hit while jumping.
            self.on_ground = not self.jumping
            self.walkable = self.cast.normal.y >= self.min_ground_normal_y
        else:
            self.on_ground = False
            self.walkable = False

    def _apply_friction(self, dt):
        if not self.on_ground:
            return
        speed = self.velocity.length
        if speed < self.min_speed:
            self.velocity = Vec2(0, self.velocity.y)
            return
        # Proportional above stop_speed, a fixed amount below it, so the
        # character comes to a stop rather than creeping.
        control = max(speed, self.stop_speed)
        new_speed = max(0.0, speed - control * self.friction * dt)
        self.velocity = Vec2(self.velocity.x * new_speed / speed, self.velocity.y)

    def _force_budget(self):
        if self.on_ground:
            return self.max_ground_force if self.walkable else 0.0
        return self.max_air_force

    def _accelerate(self, dt, throttle):
        wanted = self.max_speed * max(-1.0, min(1.0, throttle))
        if wanted == 0:
            return
        direction = math.copysign(1.0, wanted)
        add_speed = abs(wanted) - self.velocity.x * direction
        if add_speed <= 0:
            return
        steer = 1.0 if self.walkable else self.air_steer
        accel_speed = min(steer * self.accelerate * self.max_speed * dt, add_speed)
        self.velocity = Vec2(self.velocity.x + accel_speed * direction, self.velocity.y)

    def _rebuild_pogo(self):
        """Replace last step's pogo with one where the ray landed this step."""
        if self.pogo_joint is not None:
            if self.pogo_joint.is_valid:
                self.pogo_length = self.pogo_joint.length
                self.pogo_impulse = self.pogo_joint.impulse
                self.pogo_velocity = self.pogo_joint.velocity
                self.pogo_joint.destroy()
            self.pogo_joint = None

        if self.cast is None:
            self.pogo_impulse = 0.0
            self.pogo_velocity = 0.0
            return

        weight = self.gravity_scale * self.world.gravity.length * self.body.mass
        ground = self.cast.shape.body
        self.pogo_joint = self.world.add_pogo_joint(
            ground,
            self.body,
            local_anchor_a=ground.get_local_point(self.cast.point),
            local_anchor_b=self.center1,
            normal=self.cast.normal,
            rest_length=self.pogo_rest_length,
            hertz=self.pogo_hertz,
            damping_ratio=self.pogo_damping_ratio,
            max_compression_force=self.pogo_compression_scale * weight,
            # A jumping character must not be pulled back down to the ground.
            max_tension_force=(
                0.0 if self.jumping else self.pogo_tension_scale * weight
            ),
            # Carry the spring on from the joint just destroyed.
            impulse=self.pogo_impulse,
            velocity=self.pogo_velocity,
            collide_connected=True,
        )
