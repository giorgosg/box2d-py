# debug_draw.py
from ._box2d import ffi, lib
from .vec2 import Vec2

class Color:
    def __init__(self, hex_color: int):
        self._hex = hex_color
        self.r = (hex_color >> 16) & 0xFF
        self.g = (hex_color >> 8) & 0xFF
        self.b = hex_color & 0xFF
        self.a = 255  # Alpha not part of b2HexColor, default opaque

    @property
    def hex(self) -> int:
        return self._hex

    def __repr__(self) -> str:
        return f"Color(r={self.r}, g={self.g}, b={self.b}, a={self.a})"


# Define callback wrappers
def draw_polygon(vertices, count, color, context):
    instance = ffi.from_handle(context)
    instance._draw_polygon(vertices, count, Color(color))

def draw_solid_polygon(transform, vertices, count, radius, color, context):
    instance = ffi.from_handle(context)
    instance._draw_solid_polygon(transform, vertices, count, radius, Color(color))

def draw_circle(center, radius, color, context):
    instance = ffi.from_handle(context)
    instance._draw_circle(center, radius, Color(color))

def draw_segment(p1, p2, color, context):
    instance = ffi.from_handle(context)
    instance._draw_segment(p1, p2, Color(color))

def draw_point(p, size, color, context):
    instance = ffi.from_handle(context)
    instance._draw_point(p, size, Color(color))

def draw_string(p, s, color, context):
    instance = ffi.from_handle(context)
    # Convert C string to Python string
    py_str = ffi.string(s).decode('utf-8')
    instance._draw_string(p, py_str, Color(color))

def draw_capsule(p1, p2, radius, color, context):
    instance = ffi.from_handle(context)
    instance._draw_capsule(p1, p2, radius, Color(color))

def draw_solid_capsule(p1, p2, radius, color, context):
    instance = ffi.from_handle(context)
    instance._draw_solid_capsule(p1, p2, radius, Color(color))

def draw_solid_circle(transform, radius, color, context):
    instance = ffi.from_handle(context)
    instance._draw_solid_circle(transform, radius, Color(color))

def draw_transform(transform, context):
    instance = ffi.from_handle(context)
    instance._draw_transform(Transform(transform))

class DebugDraw:
    def __init__(self):
        # Create a C b2DebugDraw instance
        self._debug_draw = lib.b2DefaultDebugDraw()
        self._callbacks = {}
        self._debug_draw.context = ffi.new_handle(self)
   

        # Keep the callbacks in a dictionary so they don't get garbage collected
        self._callbacks['DrawPolygon'] = ffi.callback(
            "void(b2Vec2*, int, b2HexColor, void*)", 
            draw_polygon
        )
        self._debug_draw.DrawPolygon = self._callbacks['DrawPolygon']

        self._callbacks['DrawSolidPolygon'] = ffi.callback(
            "void(b2Transform, b2Vec2*, int, float, b2HexColor, void*)", 
            draw_solid_polygon
        )
        self._debug_draw.DrawSolidPolygon = self._callbacks['DrawSolidPolygon']

        self._callbacks['DrawCircle'] = ffi.callback(
            "void(b2Vec2, float, b2HexColor, void*)", 
            draw_circle
        )
        self._debug_draw.DrawCircle = self._callbacks['DrawCircle']

        self._callbacks['DrawSegment'] = ffi.callback(
            "void(b2Vec2, b2Vec2, b2HexColor, void*)", 
            draw_segment
        )
        self._debug_draw.DrawSegment = self._callbacks['DrawSegment']

        self._callbacks['DrawPoint'] = ffi.callback(
            "void(b2Vec2, float, b2HexColor, void*)", 
            draw_point
        )
        self._debug_draw.DrawPoint = self._callbacks['DrawPoint']

        self._callbacks['DrawString'] = ffi.callback(
            "void(b2Vec2, const char*, b2HexColor, void*)", 
            draw_string
        )
        self._debug_draw.DrawString = self._callbacks['DrawString']

        self._callbacks['DrawCapsule'] = ffi.callback(
            "void(b2Vec2, b2Vec2, float, b2HexColor, void*)", 
            draw_capsule
        )
        # there is no DrawCapsule despite the documentation
        #self._debug_draw.DrawCapsule = self._callbacks['DrawCapsule']

        self._callbacks['DrawSolidCapsule'] = ffi.callback(
            "void(b2Vec2, b2Vec2, float, b2HexColor, void*)", 
            draw_solid_capsule
        )
        self._debug_draw.DrawSolidCapsule = self._callbacks['DrawSolidCapsule']

        self._callbacks['DrawSolidCircle'] = ffi.callback(
            "void(b2Transform, float, b2HexColor, void*)", 
            draw_solid_circle
        )
        self._debug_draw.DrawSolidCircle = self._callbacks['DrawSolidCircle']

        self._callbacks['DrawTransform'] = ffi.callback(
            "void(b2Transform, void*)", 
            draw_transform
        )
        self._debug_draw.DrawTransform = self._callbacks['DrawTransform']
  
        # Store a handle to this Python object for context
        self._context_handle = ffi.new_handle(self)
        self._debug_draw.context = self._context_handle

    @property
    def draw_shapes(self):
        return bool(self._debug_draw.drawShapes)

    @draw_shapes.setter
    def draw_shapes(self, value: bool):
        self._debug_draw.drawShapes = bool(value)

    @property
    def draw_aabbs(self):
        return bool(self._debug_draw.drawAABBs)

    @draw_aabbs.setter
    def draw_aabbs(self, value: bool):
        self._debug_draw.drawAABBs = bool(value)

    @property
    def draw_joints(self):
        return bool(self._debug_draw.drawJoints)

    @draw_joints.setter
    def draw_joints(self, value: bool):
        self._debug_draw.drawJoints = bool(value)

    @property
    def draw_contacts(self):
        return bool(self._debug_draw.drawContacts)

    @draw_contacts.setter
    def draw_contacts(self, value: bool):
        self._debug_draw.drawContacts = bool(value)

    @property
    def draw_contact_normals(self):
        return bool(self._debug_draw.drawContactNormals)

    @draw_contact_normals.setter
    def draw_contact_normals(self, value: bool):
        self._debug_draw.drawContactNormals = bool(value)

    @property
    def draw_contact_impulses(self):
        return bool(self._debug_draw.drawContactImpulses)

    @draw_contact_impulses.setter
    def draw_contact_impulses(self, value: bool):
        self._debug_draw.drawContactImpulses = bool(value)

    @property
    def draw_friction_impulses(self):
        return bool(self._debug_draw.drawFrictionImpulses)

    @draw_friction_impulses.setter
    def draw_friction_impulses(self, value: bool):
        self._debug_draw.drawFrictionImpulses = bool(value)

    @property
    def draw_mass(self):
        return bool(self._debug_draw.drawMass)

    @draw_mass.setter
    def draw_mass(self, value: bool):
        self._debug_draw.drawMass = bool(value)

    @property
    def draw_joint_extras(self):
        return bool(self._debug_draw.drawJointExtras)

    @draw_joint_extras.setter
    def draw_joint_extras(self, value: bool):
        self._debug_draw.drawJointExtras = bool(value)

    # Internal callback handlers (override these in subclasses)
    def _draw_polygon(self, vertices, vertex_count, color):
        """Called by C to draw a polygon outline."""
        pass  # Override in subclass

    def _draw_solid_polygon(self, transform, vertices, vertex_count, radius, color):
        """Called by C to draw a filled polygon."""
        pass

    def _draw_circle(self, center, radius, color):
        """Called by C to draw a circle outline."""
        pass

    def _draw_segment(self, p1, p2, color):
        """Draw a line segment"""
        pass

    def _draw_point(self, p, size, color):
        """Draw a point"""
        pass

    def _draw_string(self, p, s, color):
        """Draw text"""
        pass

    def _draw_capsule(self, p1, p2, radius, color):
        """Draw the outline of a capsule"""
        pass

    def _draw_solid_capsule(self, p1, p2, radius, color):
        """Draw a solid capsule"""
        pass

    def _draw_solid_circle(self, transform, radius, color):
        """Draw a solid circle (with transform)"""
        pass

    def _draw_transform(self, transform):
        """Draw a transform indicator"""
        pass
   # Add other callback handlers...