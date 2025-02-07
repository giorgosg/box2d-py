from box2d._box2d import lib as _b2d
from box2d._box2d import ffi
from box2d.shape import *

DYNAMIC = _b2d.b2_dynamicBody
STATIC = _b2d.b2_staticBody
KINEMATIC = _b2d.b2_kinematicBody

class Body():
    def __init__(self, world, position=None, type=None):
        """
        bool	allowFastRotation	This allows this body to bypass rotational speed limits.
            Should only be used for circular objects, like wheels.

        float	angularDamping	Angular damping is use to reduce the angular velocity.
            The damping parameter can be larger than 1.0f but the damping effect becomes
            sensitive to the time step when the damping parameter is large. Angular
            damping can be use slow down rotating bodies.

        float	angularVelocity	The initial angular velocity of the body. Radians per second.
        bool	automaticMass	Automatically compute mass and related properties on this body from
            shapes.
            Triggers whenever a shape is add/removed/changed. Default is true.

        bool	enableSleep	Set this flag to false if this body should never fall asleep.
        bool	fixedRotation	Should this body be prevented from rotating? Useful for characters.
        float	gravityScale	Scale the gravity applied to this body. Non-dimensional.
        int32_t	internalValue	Used internally to detect a valid definition. DO NOT SET.
        bool	isAwake	Is this body initially awake or sleeping?
        bool	isBullet	Treat this body as high speed object that performs continuous collision
            detection against dynamic and kinematic bodies, but not other bullet bodies.
            Warning
            Bullets should be used sparingly. They are not a solution for general
            dynamic-versus-dynamic continuous collision. They may interfere with joint constraints.
        bool	isEnabled	Used to disable a body. A disabled body does not move or collide.
        float	linearDamping	Linear damping is use to reduce the linear velocity.
            The damping parameter can be larger than 1 but the damping effect becomes sensitive to
            the time step when the damping parameter is large. Generally linear damping is
            undesirable because it makes objects move slowly as if they are floating.

        b2Vec2	linearVelocity	The initial linear velocity of the body's origin. Typically in meters per second.
        b2Vec2	position	The initial world position of the body.
            Bodies should be created with the desired position.

            Note
            Creating bodies at the origin and then moving them nearly doubles the cost of body creation, especially if the body is moved after shapes have been added.
        b2Rot	rotation	The initial world rotation of the body. Use b2MakeRot() if you have an angle.
        float	sleepThreshold	Sleep velocity threshold, default is 0.05 meter per second.
        b2BodyType	type	The body type: static, kinematic, or dynamic.
        void *	userData	Use this to store application specific body data.
        """

        bodydef = _b2d.b2DefaultBodyDef()
        if position is not None:
            bodydef.position = position
        if type is not None:
            bodydef.type=type

        self.body_id = _b2d.b2CreateBody(world.world_id, ffi.addressof(bodydef))

    def create_box(self, dimensions=None, **kwargs):
        box = Box(self, dimensions, **kwargs)
        return self
