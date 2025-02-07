from box2d._box2d import lib as _b2d
from box2d._box2d import ffi
from box2d.body import Body

class World:
    def __init__(self, gravity=None):
        """
        float	contactDampingRatio	Contact bounciness. Non-dimensional.
        float	contactHertz	Contact stiffness. Cycles per second.
        float	contactPushoutVelocity	This parameter controls how fast overlap is resolved and has units of meters per second.
        bool	enableContinuous	Enable continuous collision.
        bool	enableSleep	Can bodies go to sleep to improve performance.
        b2EnqueueTaskCallback *	enqueueTask	Function to spawn tasks.
        b2FinishTaskCallback *	finishTask	Function to finish a task.
        b2Vec2	gravity	Gravity vector. Box2D has no up-vector defined.
        float	hitEventThreshold	Threshold velocity for hit events. Usually meters per second.
        int32_t	internalValue	Used internally to detect a valid definition. DO NOT SET.
        float	jointDampingRatio	Joint bounciness. Non-dimensional.
        float	jointHertz	Joint stiffness. Cycles per second.
        float	maximumLinearVelocity	Maximum linear velocity. Usually meters per second.
        float	restitutionThreshold	Restitution velocity threshold, usually in m/s.
            Collisions above this speed have restitution applied (will bounce).
        void *	userTaskContext	User context that is provided to enqueueTask and finishTask.
        int32_t	workerCount	Number of workers to use with the provided task system.
            Box2D performs best when using only performance cores and accessing a single L2 cache.
            Efficiency cores and hyper-threading provide little benefit and may even harm performance.
        """

        wdef = _b2d.b2DefaultWorldDef()
        if gravity is not None:
            wdef.gravity = gravity

        self.world_id = _b2d.b2CreateWorld(ffi.addressof(wdef))

    def create_body(self, **kwargs):
        return Body(self, **kwargs)
