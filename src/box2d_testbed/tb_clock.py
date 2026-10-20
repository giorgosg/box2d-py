import math

from box2d import Color, CollisionFilter, Vec2

from .base_test import UI, BaseTest

# Collision categories. Each pair of parts that work on each other has a pair
# of bits of its own, so that wheels which overlap in the drawing pass through
# each other, as if they sat in different planes, and touch only where they
# mesh. Every part also takes PICK, the category the mouse queries with, so
# any of them can be grabbed.
PICK = 0x0001
PALLET, ESCAPE_TEETH = 0x0002, 0x0004
ESCAPE_PINION, THIRD_TEETH = 0x0008, 0x0010
THIRD_PINION, CENTER_TEETH = 0x0020, 0x0040
DRIVE_PINION, RACK_TEETH = 0x0080, 0x0100
CANNON_PINION, MINUTE_TEETH = 0x0200, 0x0400
MINUTE_PINION, HOUR_TEETH = 0x0800, 0x1000
#: Everything that is only there to be seen: rods, hubs, hands, the weight.
DECOR = 0x8000

BRASS = Color(214, 170, 72)
STEEL = Color(150, 160, 175)
ESCAPE_BRASS = Color(240, 200, 90)
HAND = Color(235, 235, 235)
SECONDS_HAND = Color(220, 70, 60)
DIAL = Color(120, 120, 130)
LEAD = Color(90, 90, 100)

#: Every tooth slides on another, so friction costs some of the drive.
FRICTION = 0.1


def meshing(category, partner):
    """A filter for teeth that touch ``partner``'s teeth and nothing else."""
    return CollisionFilter(category=category, mask=partner | PICK)


def decor():
    return CollisionFilter(category=DECOR, mask=PICK)


def polar(radius, angle):
    return Vec2(radius * math.cos(angle), radius * math.sin(angle))


def add_hand(builder, length, width, tail, angle, colour, density=0.0):
    """Add a hand to a body being built, pointing along ``angle``.

    Weightless unless given a density. A hand that weighs anything pulls its
    wheel round to point down, and a real one is balanced by a counterweight
    on its tail so that it does not.
    """
    builder.box(
        width,
        length + tail,
        offset=polar((length - tail) / 2, angle),
        angle=angle - math.pi / 2,
        density=density,
        filter=decor(),
        custom_color=colour,
    )


def clock_angle(hours):
    """The angle a hand pointing at ``hours`` on a 12-hour dial points along."""
    return math.pi / 2 - hours * math.pi / 6


def add_gear(builder, teeth, module, phase, filter, colour, center=(0, 0)):
    """Add a gear's teeth and hub to a body being built.

    The teeth are trapezoids with rounded corners: no involute, but cut thin
    enough to leave room between them, they roll through each other well
    enough. ``module`` sets their size, as an engineer's gear module does: a
    gear's pitch radius is module * teeth / 2, so two gears of the same
    module mesh at the sum of their pitch radii. ``phase`` is the angle the
    first tooth points along, in the body's own frame.

    Returns the pitch radius.
    """
    pitch_radius = module * teeth / 2
    tip, root = pitch_radius + module, pitch_radius - 1.25 * module
    pitch = 2 * math.pi / teeth
    rounding = 0.01
    # Half the tooth's thickness at its root and tip. Under half a pitch at
    # the pitch circle, so meshing teeth have play between them.
    half_root = 0.27 * pitch * root - rounding
    half_tip = max(0.12 * pitch * tip - rounding, 0.005)
    inner, outer = root + rounding, tip - rounding
    center = Vec2(center)
    for i in range(teeth):
        angle = phase + i * pitch
        out, side = polar(1, angle), polar(1, angle + math.pi / 2)
        builder.polygon(
            [
                center + out * inner - side * half_root,
                center + out * outer - side * half_tip,
                center + out * outer + side * half_tip,
                center + out * inner + side * half_root,
            ],
            radius=rounding,
            friction=FRICTION,
            filter=filter,
            custom_color=colour,
        )
    builder.circle(root, center=center, filter=decor(), custom_color=colour)
    return pitch_radius


class PendulumClock(BaseTest, category="Machines", name="Pendulum Clock"):
    """A pendulum clock movement, driven by a falling weight and nothing else.

    Gravity does all of it. The weight hangs from a toothed rack, which
    turns the center wheel as it sinks; the center wheel turns the third
    wheel, and the third wheel the escape wheel at the top, each through a
    small pinion on the faster wheel's arbor. Left to itself the train
    would spin away and the weight drop to the floor. The escapement stops
    it: two pins on the pendulum's anchor reach into the escape wheel's
    teeth, and whichever is in holds the wheel. As the pendulum swings, that
    pin draws out and lets one tooth go, and the wheel jumps on until the
    other pin, swinging in, catches the next one. The weight comes
    down a little at every swing, the hands go round a step at a time, and
    the pendulum, not the weight, sets how fast.

    Something has to keep the pendulum going, too, or friction and the
    knocks of the teeth would stop it. A tooth leaving its pin slides along
    under it on its sloping tip and so pushes the pin out of the way: a
    shove in the direction the pendulum is already swinging. Those shoves
    are where the weight's energy goes, and the swing settles where they
    make up for what each swing loses. A heavier weight pushes harder and
    the swing grows, but slowly: 2 kg swings it about 6 degrees either way,
    and forty times that not quite twice as far.

    The red seconds hand is on the escape wheel, which turns a tooth for
    every two swings and so once every 30. The long minute hand is on the
    center wheel, 60 times slower. The short hour hand is on a wheel of its
    own, turned 12 times slower again by the motion work: the cannon pinion
    on the center wheel, the minute wheel beside it, and the minute wheel's
    pinion. None of it keeps true time. The pendulum is 7 m long and takes
    about 2.6 s a swing, so the "minute" is nearly 80 seconds long.

    The weight falls 4.5 m in about an hour and a half, and then the clock
    stops: the train can turn no further, and sooner or later the pendulum
    is caught leaning on a tooth. Wind lifts the weight back to the top, as
    winding a real clock would, and as with a real clock the pendulum then
    wants a push to set it going: Push gives it one, or drag it. Weight is the
    weight's mass, in kg. With none at all the train stops, and the
    pendulum swings on by itself, a little less each time its pins brush
    the teeth.

    Wheels that overlap sit in different planes, as in a real movement,
    and touch only where their teeth mesh.
    """

    camera_center = (0.6, -2.2)
    camera_zoom = 6.0

    #: The escape wheel: tooth count, tip radius, and the radius the sloping
    #: tips start from, which the pins are pushed out from, in m.
    ESCAPE_TEETH = 15
    ESCAPE_RADIUS = 1.0
    ESCAPE_TIP_START = 0.93
    ESCAPE_ROOT = 0.6
    #: How many teeth apart the two pins are. Half a tooth over a whole
    #: number, so when one pin is holding a tooth the other is over a gap.
    PIN_SPAN = 4.5
    #: How far out the pins sit from the escape wheel's center, and their
    #: radius, in m.
    PIN_RADIUS = 0.945
    PIN_SIZE = 0.04
    #: Pivot to bob, in m, and the bob's radius.
    PENDULUM_LENGTH = 7.0
    BOB_RADIUS = 0.5
    #: The pendulum starts this far over, in radians: a clock has to be set
    #: swinging.
    START_ANGLE = 0.1
    #: The time the hands start at, as (hours, minutes): ten past ten, as
    #: in a clockmaker's window, for the reason given in build_motion_work.
    START_TIME = (10, 10)
    #: How fast Push sets the pendulum swinging, in rad/s: about as fast as
    #: it goes through the middle of a swing 8 degrees either way.
    PUSH_SPEED = 0.17
    #: How far the weight can fall, in m, before the rack runs out.
    RUN = 4.5
    #: Light, so the rack weighs next to nothing and the weight is all
    #: there is to drive the clock.
    RACK_DENSITY = 0.05

    weight = UI.float(25.0, min=0.0, max=80.0, label="Weight (kg)")
    wind = UI.button("Wind")
    push = UI.button("Push")

    def setup(self):
        self.ground = self.world.new_body().static().build()
        self.swings = 0
        self.swinging_right = None
        self.amplitude = self.START_ANGLE

        pitch = 2 * math.pi / self.ESCAPE_TEETH
        half_span = self.PIN_SPAN * pitch / 2
        # Put the pivot where each pin moves straight in and out of the
        # wheel, not along it: where the line to the pivot is square to the
        # line to the wheel's center.
        self.pivot = Vec2(0.0, self.ESCAPE_RADIUS / math.cos(half_span))

        self.build_pendulum(half_span)
        self.build_escape_wheel(pitch)
        self.build_train()
        self.build_motion_work()
        self.build_weight()

    def build_pendulum(self, half_span):
        length = self.PENDULUM_LENGTH
        pendulum = (
            self.world.new_body()
            .dynamic()
            .position(*self.pivot)
            .rotation(self.START_ANGLE)
            .box(
                0.05,
                length,
                offset=(0, -length / 2),
                filter=decor(),
                custom_color=STEEL,
            )
            .circle(
                self.BOB_RADIUS,
                center=(0, -length),
                density=10.0,
                filter=decor(),
                custom_color=BRASS,
            )
        )
        self.pins = []
        for side in (-1, 1):
            pin = polar(self.PIN_RADIUS, math.pi / 2 + side * half_span) - self.pivot
            self.pins.append(pin)
            # The anchor's arm, out to the pin.
            pendulum.capsule(
                (0, 0), pin, radius=0.03, filter=decor(), custom_color=STEEL
            )
            pendulum.circle(
                self.PIN_SIZE,
                center=pin,
                friction=FRICTION,
                filter=meshing(PALLET, ESCAPE_TEETH),
                custom_color=STEEL,
            )
        self.pendulum = pendulum.build()
        self.world.add_revolute_joint(self.ground, self.pendulum, anchor=self.pivot)

    def build_escape_wheel(self, pitch):
        # Turned so that a tooth is just about to land on the left pin, which
        # the pendulum's start angle has pushed in between two teeth. The
        # tooth's front face is radial, and touches the pin side on.
        left_pin = self.pendulum.get_world_point(self.pins[0])
        touching = math.asin(self.PIN_SIZE / left_pin.length)
        face = math.atan2(left_pin.y, left_pin.x) + touching + math.radians(0.3)
        self.escape_rotation = face % pitch

        wheel = self.world.new_body().dynamic().rotation(self.escape_rotation)
        # Each tooth has a radial face on its clockwise side, which the pins
        # stop, and a tip sloping up from there, which pushes them out.
        teeth = meshing(ESCAPE_TEETH, PALLET)
        root, tip = self.ESCAPE_ROOT, 0.2 * pitch
        for i in range(self.ESCAPE_TEETH):
            angle = i * pitch
            wheel.polygon(
                [
                    polar(root, angle),
                    polar(self.ESCAPE_TIP_START, angle),
                    polar(self.ESCAPE_RADIUS, angle + tip),
                    polar(root, angle + tip),
                ],
                friction=FRICTION,
                filter=teeth,
                custom_color=ESCAPE_BRASS,
            )
        wheel.circle(root, filter=decor(), custom_color=ESCAPE_BRASS)
        add_hand(wheel, 0.85, 0.03, 0.2, math.pi / 2, SECONDS_HAND)
        self.escape_wheel = wheel
        # Its pinion is added once the third wheel's place is known.

    def build_train(self):
        # The escape wheel's pinion, and the third wheel down and to its
        # left, with a tooth pointing straight into the pinion's gap. Gears
        # are phased in their body's own frame, and only the escape wheel
        # starts turned.
        to_third = math.radians(-120)
        add_gear(
            self.escape_wheel,
            8,
            0.05,
            to_third - self.escape_rotation + math.pi / 8,
            meshing(ESCAPE_PINION, THIRD_TEETH),
            STEEL,
        )
        self.escape_wheel = self.escape_wheel.build()
        self.pin_to_ground(self.escape_wheel)

        third_center = polar(0.05 * (8 + 60) / 2, to_third)
        to_center = math.radians(-30)
        third = self.world.new_body().dynamic().position(*third_center)
        add_gear(
            third,
            60,
            0.05,
            to_third + math.pi,
            meshing(THIRD_TEETH, ESCAPE_PINION),
            BRASS,
        )
        add_gear(
            third,
            8,
            0.05,
            to_center + math.pi / 8,
            meshing(THIRD_PINION, CENTER_TEETH),
            STEEL,
        )
        self.third_wheel = third.build()
        self.pin_to_ground(self.third_wheel)

        # The center wheel carries the minute hand, the pinion the rack
        # drives, and the cannon pinion that drives the motion work.
        self.center = third_center + polar(0.05 * (8 + 64) / 2, to_center)
        center = self.world.new_body().dynamic().position(*self.center)
        add_gear(
            center,
            64,
            0.05,
            to_center + math.pi,
            meshing(CENTER_TEETH, THIRD_PINION),
            BRASS,
        )
        # A gap facing the rack, on the right.
        self.drive_radius = add_gear(
            center,
            16,
            0.08,
            math.pi / 16,
            meshing(DRIVE_PINION, RACK_TEETH),
            STEEL,
        )
        self.to_minute_wheel = math.radians(-150)
        add_gear(
            center,
            8,
            0.05,
            self.to_minute_wheel,
            meshing(CANNON_PINION, MINUTE_TEETH),
            STEEL,
        )
        add_hand(center, 1.45, 0.06, 0.25, clock_angle(self.START_TIME[1] / 5), HAND)
        self.center_wheel = center.build()
        self.pin_to_ground(self.center_wheel)

    def build_motion_work(self):
        # The minute wheel, turned by the cannon pinion 4 times slower, and
        # its pinion, turning the hour wheel 3 times slower again. The hour
        # wheel turns about the center wheel's arbor, as the hour hand does
        # about the minute hand's.
        #
        # Nothing else loads these two wheels, so they are free to rattle
        # about in the play between their teeth, and the hour hand with them.
        # So the hour hand, alone of the hands, is not balanced: its weight
        # presses its wheel's teeth against the pinion's one way or the
        # other -- except with the hand straight up or down, which is why the
        # clock does not start at twelve.
        out = self.to_minute_wheel
        minute_center = self.center + polar(0.05 * (8 + 32) / 2, out)
        minute = self.world.new_body().dynamic().position(*minute_center)
        add_gear(
            minute,
            32,
            0.05,
            out + math.pi + math.pi / 32,
            meshing(MINUTE_TEETH, CANNON_PINION),
            BRASS,
        )
        add_gear(
            minute, 8, 0.0625, out + math.pi, meshing(MINUTE_PINION, HOUR_TEETH), STEEL
        )
        self.minute_wheel = minute.build()
        self.pin_to_ground(self.minute_wheel)

        hour = self.world.new_body().dynamic().position(*self.center)
        add_gear(
            hour,
            24,
            0.0625,
            out + math.pi / 24,
            meshing(HOUR_TEETH, MINUTE_PINION),
            BRASS,
        )
        hours = self.START_TIME[0] + self.START_TIME[1] / 60
        add_hand(hour, 0.95, 0.1, 0.15, clock_angle(hours), HAND, density=1.0)
        self.hour_wheel = hour.build()
        self.pin_to_ground(self.hour_wheel)

    def build_weight(self):
        # The rack hangs on the right of the drive pinion, teeth pointing in,
        # with one tooth in the pinion's gap. Its origin is on the pitch line,
        # level with the center wheel's arbor.
        module = 0.08
        self.rack_pitch = math.pi * module
        pitch_line = self.center.x + self.drive_radius
        rack = self.world.new_body().dynamic().position(pitch_line, self.center.y)
        teeth = meshing(RACK_TEETH, DRIVE_PINION)
        rounding = 0.01
        half_root, half_tip = 0.27 * self.rack_pitch, 0.12 * self.rack_pitch
        below = 3
        above = math.ceil(self.RUN / self.rack_pitch) + 2
        for k in range(-below, above):
            y = k * self.rack_pitch
            rack.polygon(
                [
                    (-module + rounding, y - half_tip + rounding),
                    (1.25 * module - rounding, y - half_root + rounding),
                    (1.25 * module - rounding, y + half_root - rounding),
                    (-module + rounding, y + half_tip - rounding),
                ],
                radius=rounding,
                density=self.RACK_DENSITY,
                friction=FRICTION,
                filter=teeth,
                custom_color=STEEL,
            )
        bottom, top = -below * self.rack_pitch, above * self.rack_pitch
        rack.box(
            0.15,
            top - bottom,
            offset=(1.25 * module + 0.075, (top + bottom) / 2),
            density=self.RACK_DENSITY,
            filter=decor(),
            custom_color=STEEL,
        )
        rack.box(
            0.7,
            0.9,
            offset=(0.3, bottom - 0.45),
            density=self.weight_density(self.weight),
            filter=decor(),
            custom_color=LEAD,
        )
        self.rack = rack.build()
        self.lead = self.rack.shapes[-1]
        # The rack slides up and down and nothing else. The limits stop the
        # weight where the rack runs out of teeth, and Wind from lifting it
        # off the top.
        self.world.add_prismatic_joint(
            self.ground,
            self.rack,
            local_anchor_a=(pitch_line, self.center.y),
            local_anchor_b=(0, 0),
            axis=(0, 1),
            enable_limit=True,
            lower_limit=-self.RUN,
            upper_limit=self.rack_pitch,
        )

    def pin_to_ground(self, body):
        self.world.add_revolute_joint(self.ground, body, anchor=body.position)

    def weight_density(self, kilograms):
        # The weight is a 0.7 by 0.9 m block.
        return kilograms / (0.7 * 0.9)

    @property
    def fallen(self):
        """How far the weight has come down since it was last wound, in m."""
        return self.center.y - self.rack.position.y

    @weight.callback
    def on_weight_change(self, key, value):
        self.lead.density = self.weight_density(value)
        self.rack.awake = True

    @wind.callback
    def on_wind(self, key, value):
        # Lifted a whole number of teeth, so the rack meshes with the pinion
        # just as it did. A real clock has a click that lets the weight be
        # wound up without turning the train back; this lifts it instead.
        teeth = round(self.fallen / self.rack_pitch)
        self.rack.position = self.rack.position + Vec2(0, teeth * self.rack_pitch)
        self.rack.linear_velocity = (0, 0)
        self.rack.awake = True

    @push.callback
    def on_push(self, key, value):
        # A stopped pendulum is leaning on a tooth with one of its pins, and
        # pushed the other way it would only lean harder. So it is pushed to
        # lift that pin off: the left pin comes out of the wheel as the
        # pendulum turns clockwise, and the right one anticlockwise. A
        # velocity, rather than moving it, so a pin is never put down inside
        # a tooth.
        direction = -1.0 if self.pendulum.rotation > 0 else 1.0
        for contact in self.pendulum.contact_data:
            if contact.manifold.points:
                point = contact.manifold.points[0]
                where = contact.shape_a.body.world_center_of_mass + point.anchor_a
                direction = -1.0 if where.x < self.pivot.x else 1.0
        self.pendulum.angular_velocity = direction * self.PUSH_SPEED
        self.pendulum.awake = True

    def after_step(self, dt):
        # A swing ends where the pendulum turns round.
        swinging_right = self.pendulum.angular_velocity < 0
        if self.swinging_right is not None and swinging_right != self.swinging_right:
            self.swings += 1
            self.amplitude = abs(self.pendulum.rotation)
        self.swinging_right = swinging_right

    def debug_draw(self, debug_draw):
        # The minute dial, around the center wheel.
        for minute in range(60):
            angle = math.pi / 2 - minute * math.pi / 30
            inner = 1.85 if minute % 5 else 1.75
            debug_draw.draw_segment(
                self.center + polar(inner, angle),
                self.center + polar(1.95, angle),
                DIAL,
            )

    def status(self):
        left = min(max(0.0, 1 - self.fallen / self.RUN), 1.0)
        return (
            f"swings: {self.swings}   "
            f"swinging {math.degrees(self.amplitude):.1f} deg either way   "
            f"weight left to fall: {left:.0%}"
        )
