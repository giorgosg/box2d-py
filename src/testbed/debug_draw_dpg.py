import math
import dearpygui.dearpygui as dpg
from box2d import Vec2, DebugDraw, Color, ScaledTransform

class DearpyguiDebugDraw(DebugDraw):
    """
    A concrete implementation of DebugDraw using Dear PyGui.
    """
    def __init__(self, canvas):
        # canvas: an item id of a dpg.drawlist
        super().__init__()
        self.canvas = canvas
        self.draw_shapes = True
        self.draw_joints = True
        self.outline_thickness = 1  # use thicker outlines, if desired

        self.view_transform = ScaledTransform(
            position=(400, 300),
            rotation=0,
            scale=(30, -30)
        )

    def round_polygon_vertices(self, vertices, radius):
        """Calculate new vertices to form a rounded polygon."""
        # Convert the physical radius to screen pixels.
        screen_r = round(radius * abs(self.view_transform._scale.x))
        arc_segments_max = max(screen_r * 2, 2)
        outline_points = []
        n = len(vertices)
        for i, v in enumerate(vertices):
            prev = vertices[i - 1]
            nxt = vertices[(i + 1) % n]
            # Compute unit directions along incoming/outgoing edges.
            d_prev = (v - prev).normalize()
            d_next = (nxt - v).normalize()
            # Outward normals: rotate each edge 90° clockwise.
            n_prev = d_prev.perpendicular('right')
            n_next = d_next.perpendicular('right')
            # Calculate the angles in [0, 2π)
            a1 = n_prev.angle % (2 * math.pi)
            a2 = n_next.angle % (2 * math.pi)
            if a2 < a1:
                a2 += 2 * math.pi
            # Determine the fraction of the full circle and the number of segments.
            arc_fraction = (a2 - a1) / (2 * math.pi)
            arc_segments = max(round(arc_fraction * arc_segments_max), 2)
            # Generate arc corner points.
            arc_points = [
                v + Vec2.from_angle(a1 + t * (a2 - a1)) * radius
                for t in (j / arc_segments for j in range(arc_segments + 1))
            ]
            # For all but the first vertex, skip the duplicate start point.
            if i == 0:
                outline_points.extend(arc_points)
            else:
                outline_points.extend(arc_points[1:])
        return outline_points

    def draw_polygon(self, vertices: list[Vec2], color: Color):
        if len(vertices) < 2:
            return
        # Transform each vertex to screen space and round its coordinates.
        points = [tuple(round(self.view_transform(v)))
                  for v in vertices]
        points.append(points[0])
        dpg.draw_polygon(points,
                         color=tuple(color),
                         thickness=self.outline_thickness,
                         parent=self.canvas)

    def draw_solid_polygon(self, transform, vertices, radius, color: Color):
        # If radius is visible on screen, use rounded polygon vertices.
        screen_r = round(radius * abs(self.view_transform._scale.x))
        if screen_r != 0:
            vertices = self.round_polygon_vertices(vertices, radius)
        # Apply the local transform to each vertex.
        transformed = [transform(v) for v in vertices]
        points = [tuple(round(self.view_transform(v)))
                  for v in transformed]
        points.append(points[0])
        base = (color.r, color.g, color.b)
        line_color = tuple(min(255, c + 100) for c in base) + (255,)
        dpg.draw_polygon(points,
                         fill=tuple(color)[:3] + (150,),
                         color=line_color,
                         thickness=self.outline_thickness,
                         parent=self.canvas)

    def draw_string(self, p: Vec2, s, color: Color):
        pos = tuple(round(self.view_transform(p)))
        dpg.draw_text(pos, s,
                      color=tuple(color),
                      size=14,
                      parent=self.canvas)

    def draw_circle(self, center: Vec2, radius: float, color: Color):
        center_screen = tuple(round(self.view_transform(center)))
        scaled_radius = round(radius * abs(self.view_transform._scale.x))
        dpg.draw_circle(center=center_screen,
                        radius=scaled_radius,
                        color=tuple(color),
                        thickness=self.outline_thickness,
                        parent=self.canvas)

    def draw_solid_circle(self, transform, radius, color: Color):
        center = transform.p
        # Use the rotation's angle via the math module's interface.
        angle = transform.q.angle_radians
        center_screen = tuple(round(self.view_transform(center)))
        scaled_radius = round(radius * abs(self.view_transform._scale.x))
        fill_color = tuple(color)[:3] + (150,)
        base = (color.r, color.g, color.b)
        line_color = tuple(min(255, c + 100) for c in base) + (255,)
        dpg.draw_circle(center=center_screen,
                        radius=scaled_radius,
                        fill=fill_color,
                        color=line_color,
                        thickness=self.outline_thickness,
                        parent=self.canvas)
        # Draw the orientation line using the rotation's x_axis.
        edge_vector = transform.q.x_axis * scaled_radius
        edge_point = (
            center_screen[0] + round(edge_vector.x),
            center_screen[1] - round(edge_vector.y)
        )
        dpg.draw_line(center_screen, edge_point,
                      color=line_color,
                      thickness=self.outline_thickness,
                      parent=self.canvas)

    def draw_segment(self, p1: Vec2, p2: Vec2, color: Color):
        sp1 = tuple(round(self.view_transform(p1)))
        sp2 = tuple(round(self.view_transform(p2)))
        dpg.draw_line(sp1, sp2,
                      color=tuple(color),
                      thickness=self.outline_thickness,
                      parent=self.canvas)

    def draw_transform(self, transform):
        p = transform.p
        # Use the rotation's x_axis and y_axis to determine the coordinate axes.
        p1 = p
        p2 = p + transform.q.x_axis
        p3 = p + transform.q.y_axis
        sp1 = tuple(round(self.view_transform(p1)))
        sp2 = tuple(round(self.view_transform(p2)))
        sp3 = tuple(round(self.view_transform(p3)))
        dpg.draw_line(sp1, sp2,
                      color=(255, 0, 0, 255),
                      thickness=self.outline_thickness,
                      parent=self.canvas)
        dpg.draw_line(sp1, sp3,
                      color=(0, 255, 0, 255),
                      thickness=self.outline_thickness,
                      parent=self.canvas)

    def draw_point(self, p: Vec2, size: float, color: Color):
        screen_pos = round(self.view_transform(p)).as_tuple
        dpg.draw_circle(center=screen_pos,
                        radius=max(1, size),
                        fill=tuple(color),
                        thickness=0,
                        parent=self.canvas)

    def draw_solid_capsule(self, p1: Vec2, p2: Vec2, radius: float, color: Color):
        sp1 = tuple(round(self.view_transform(p1)))
        sp2 = tuple(round(self.view_transform(p2)))
        sr = max(1, round(radius * abs(self.view_transform._scale.x)))
        # Calculate the perpendicular direction in screen space.
        diff = Vec2(sp2[0] - sp1[0], sp2[1] - sp1[1])
        length = diff.length
        perp = diff.perpendicular('right').normalize() if length != 0 else Vec2.zero()
        offset = perp * sr
        p1_plus  = (sp1[0] + round(offset.x), sp1[1] + round(offset.y))
        p1_minus = (sp1[0] - round(offset.x), sp1[1] - round(offset.y))
        p2_plus  = (sp2[0] + round(offset.x), sp2[1] + round(offset.y))
        p2_minus = (sp2[0] - round(offset.x), sp2[1] - round(offset.y))
        fill_color = tuple(color)
        dpg.draw_polygon([p1_plus, p2_plus, p2_minus, p1_minus],
                         fill=fill_color,
                         thickness=0,
                         parent=self.canvas)
        dpg.draw_circle(center=sp1,
                        radius=sr,
                        fill=fill_color,
                        thickness=0,
                        parent=self.canvas)
        dpg.draw_circle(center=sp2,
                        radius=sr,
                        fill=fill_color,
                        thickness=0,
                        parent=self.canvas)
        outline_color = tuple(min(255, c + 50) for c in (color.r, color.g, color.b)) + (255,)
        dpg.draw_polyline([p1_plus, p2_plus, p2_minus, p1_minus],
                          color=outline_color,
                          thickness=self.outline_thickness,
                          closed=True,
                          parent=self.canvas)
        dpg.draw_circle(center=sp1,
                        radius=sr,
                        color=outline_color,
                        thickness=self.outline_thickness,
                        parent=self.canvas)
        dpg.draw_circle(center=sp2,
                        radius=sr,
                        color=outline_color,
                        thickness=self.outline_thickness,
                        parent=self.canvas)
