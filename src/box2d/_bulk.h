/* Bulk exports: loops over Box2D in C that write records into memory the
 * caller owns, so a frame's worth of data costs no Python object per row.
 *
 * cffi declares this file as it stands, so it holds only plain declarations:
 * no includes, macros or inline code. box2d/records.py describes each record
 * to Python, and a test holds the two to the same layout. */

/* One body's place: world.write_moves and world.write_transforms. 24 bytes,
 * little-endian, no padding. */
typedef struct b2pyMoveRecord
{
	uint32_t key;   /* the body's Box2D slot, bodyId.index1 */
	float x;
	float y;
	float c;        /* cosine of the angle */
	float s;        /* sine of the angle */
	uint32_t flags; /* bit 0: asleep (on a move, fell asleep on the step) */
} b2pyMoveRecord;

/* The last step's moves, leaving out bodies destroyed since. Writes as many
 * records as fit in `size` bytes and returns how many there are in all. */
int b2py_WriteMoves( b2WorldId worldId, void* buffer, size_t size );

/* The same record for each of `count` bodies, moved or not. */
int b2py_WriteTransforms( const b2BodyId* bodies, int count, void* buffer, size_t size );
