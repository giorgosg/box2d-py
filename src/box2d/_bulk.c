/* The bulk exports declared in _bulk.h. Compiled into box2d._box2d beside
 * Box2D, which is left untouched. */

#include <string.h>

#include "box2d/box2d.h"
#include "_bulk.h"

/* Records are written in the machine's byte order and documented as
 * little-endian, which every platform built for is. */
#if defined( __BYTE_ORDER__ ) && __BYTE_ORDER__ == __ORDER_BIG_ENDIAN__
#error "box2d-py's bulk records are little-endian"
#endif

/* The record holds float positions. A large-world build would need a second
 * layout, with its own version, rather than narrowing these quietly. */
#ifdef BOX2D_DOUBLE_PRECISION
#error "the move record has float positions; a double precision build needs its own"
#endif

/* Fails to compile if the record is not 24 bytes; spelt so MSVC takes it. */
typedef char b2py_RecordIs24Bytes[sizeof( b2pyMoveRecord ) == 24 ? 1 : -1];

enum
{
	b2py_asleep = 1,
};

static void b2py_WriteRecord( unsigned char* at, b2BodyId id, b2WorldTransform transform, bool asleep )
{
	b2pyMoveRecord record = {
		(uint32_t)id.index1,  (float)transform.p.x, (float)transform.p.y,
		transform.q.c,        transform.q.s,        asleep ? b2py_asleep : 0,
	};
	/* The caller's buffer need not be aligned. */
	memcpy( at, &record, sizeof record );
}

int b2py_WriteMoves( b2WorldId worldId, void* buffer, size_t size )
{
	b2BodyEvents events = b2World_GetBodyEvents( worldId );
	size_t room = size / sizeof( b2pyMoveRecord );
	unsigned char* at = buffer;
	int total = 0;
	for ( int i = 0; i < events.moveCount; ++i )
	{
		const b2BodyMoveEvent* event = events.moveEvents + i;
		/* A body destroyed since the step fails the generation check, even
		 * when a new body has taken its slot. */
		if ( b2Body_IsValid( event->bodyId ) == false )
		{
			continue;
		}
		if ( (size_t)total < room )
		{
			b2py_WriteRecord( at, event->bodyId, event->transform, event->fellAsleep );
			at += sizeof( b2pyMoveRecord );
		}
		total += 1;
	}
	return total;
}

int b2py_WriteTransforms( const b2BodyId* bodies, int count, void* buffer, size_t size )
{
	size_t room = size / sizeof( b2pyMoveRecord );
	unsigned char* at = buffer;
	for ( int i = 0; i < count && (size_t)i < room; ++i )
	{
		b2BodyId id = bodies[i];
		/* Static and disabled bodies are not awake either, but they are not
		 * asleep: only a body that can move can fall asleep. */
		bool asleep = b2Body_GetType( id ) != b2_staticBody && b2Body_IsEnabled( id ) &&
					  b2Body_IsAwake( id ) == false;
		b2py_WriteRecord( at, id, b2Body_GetTransform( id ), asleep );
		at += sizeof( b2pyMoveRecord );
	}
	return count;
}
