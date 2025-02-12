import math
import dearpygui.dearpygui as dpg
from box2d import Vec2, DebugDraw, Color, ScaledTransform, Rot


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
            position=(400, 300), rotation=0, scale=(30, -30)
        )

    def start_frame(self):
        """
        Clears the canvas at the start of a frame.
        """
        # Remove all previous drawn items.
        dpg.delete_item(self.canvas, children_only=True)
        # Get the canvas dimensions.
        canvas_width = dpg.get_item_width(self.canvas)
        canvas_height = dpg.get_item_height(self.canvas)
        # Draw a background rectangle.
        dpg.draw_rectangle(
            (0, 0),
            (canvas_width, canvas_height),
            fill=(60, 60, 60, 255),
            color=(90, 90, 90, 255),
            parent=self.canvas,
        )

    def end_frame(self):
        """
        Finalize the frame.
        Currently, this is a no-op but can be used for any post-draw operations.
        """
        pass

    def round_polygon_vertices(self, vertices, radius):
        """
        Approximates a convex CCW polygon with rounded corners.

        Replaces each sharp vertex with an arc of the specified radius, effectively smoothing
        the polygon's outline. Conceptually, this is similar to computing the Minkowski sum of
        the polygon with a circle of the given radius.
        """
        screen_r = round(radius * abs(self.view_transform._scale.x))
        base_segments = max(screen_r, 2)

        outline_points = []
        n = len(vertices)

        for i, v in enumerate(vertices):
            # Get the previous and next vertex, automatically wrapping around.
            prev = vertices[i - 1]
            next = vertices[(i + 1) % n]

            # Compute unit vectors along the incoming and outgoing edges.
            # For a CCW polygon, outward is given by a clockwise (right) rotation.
            n_prev = (v - prev).normalize().perpendicular("right")
            n_next = (next - v).normalize().perpendicular("right")

            # Calculate their angles.
            a0, a1 = n_prev.angle, n_next.angle
            arc_angle = a1 - a0

            # Determine how many segments to use for this particular arc.
            arc_segments = max(round(abs(arc_angle) / (2 * math.pi) * base_segments), 2)

            # Create starting and ending rotations.
            start_rot = Rot(a0)
            end_rot = Rot(a0 + arc_angle)

            # Generate arc points by interpolating between the start and end rotations.
            arc_points = [
                v + start_rot.interpolate(end_rot, j / arc_segments) * radius
                for j in range(arc_segments + 1)
            ]

            # Do not duplicate the shared vertex point (after the first one).
            if i > 0:
                arc_points = arc_points[1:]
            outline_points.extend(arc_points)

        return outline_points

    def draw_polygon(self, vertices: list[Vec2], color: Color):
        if len(vertices) < 2:
            return
        # Transform each vertex to screen space and round its coordinates.
        points = [tuple(round(self.view_transform(v))) for v in vertices]
        points.append(points[0])
        dpg.draw_polygon(
            points,
            color=tuple(color),
            thickness=self.outline_thickness,
            parent=self.canvas,
        )

    def draw_solid_polygon(self, transform, vertices, radius, color: Color):
        # If radius is visible on screen, use rounded polygon vertices.
        screen_r = round(radius * abs(self.view_transform._scale.x))
        if screen_r != 0:
            vertices = self.round_polygon_vertices(vertices, radius)
        # Apply the local transform to each vertex.
        transformed = [transform(v) for v in vertices]
        points = [tuple(round(self.view_transform(v))) for v in transformed]
        points.append(points[0])
        base = (color.r, color.g, color.b)
        line_color = tuple(min(255, c + 100) for c in base) + (255,)
        dpg.draw_polygon(
            points,
            fill=tuple(color)[:3] + (150,),
            color=line_color,
            thickness=self.outline_thickness,
            parent=self.canvas,
        )

    def draw_string(self, p: Vec2, s, color: Color):
        pos = tuple(round(self.view_transform(p)))
        dpg.draw_text(pos, s, color=tuple(color), size=14, parent=self.canvas)

    def draw_circle(self, center: Vec2, radius: float, color: Color):
        center_screen = tuple(round(self.view_transform(center)))
        scaled_radius = round(radius * abs(self.view_transform._scale.x))
        dpg.draw_circle(
            center=center_screen,
            radius=scaled_radius,
            color=tuple(color),
            thickness=self.outline_thickness,
            parent=self.canvas,
        )

    def draw_solid_circle(self, transform, radius, color: Color):
        center = transform.p
        # Use the rotation's angle via the math module's interface.
        angle = transform.q.angle_radians
        center_screen = tuple(round(self.view_transform(center)))
        scaled_radius = round(radius * abs(self.view_transform._scale.x))
        fill_color = tuple(color)[:3] + (150,)
        base = (color.r, color.g, color.b)
        line_color = tuple(min(255, c + 100) for c in base) + (255,)
        dpg.draw_circle(
            center=center_screen,
            radius=scaled_radius,
            fill=fill_color,
            color=line_color,
            thickness=self.outline_thickness,
            parent=self.canvas,
        )
        # Draw the orientation line using the rotation's x_axis.
        edge_vector = transform.q.x_axis * scaled_radius
        edge_point = (
            center_screen[0] + round(edge_vector.x),
            center_screen[1] - round(edge_vector.y),
        )
        dpg.draw_line(
            center_screen,
            edge_point,
            color=line_color,
            thickness=self.outline_thickness,
            parent=self.canvas,
        )

    def draw_segment(self, p1: Vec2, p2: Vec2, color: Color):
        sp1 = tuple(round(self.view_transform(p1)))
        sp2 = tuple(round(self.view_transform(p2)))
        dpg.draw_line(
            sp1,
            sp2,
            color=tuple(color),
            thickness=self.outline_thickness,
            parent=self.canvas,
        )

    def draw_transform(self, transform):
        p = transform.p
        # Use the rotation's x_axis and y_axis to determine the coordinate axes.
        p1 = p
        p2 = p + transform.q.x_axis
        p3 = p + transform.q.y_axis
        sp1 = tuple(round(self.view_transform(p1)))
        sp2 = tuple(round(self.view_transform(p2)))
        sp3 = tuple(round(self.view_transform(p3)))
        dpg.draw_line(
            sp1,
            sp2,
            color=(255, 0, 0, 255),
            thickness=self.outline_thickness,
            parent=self.canvas,
        )
        dpg.draw_line(
            sp1,
            sp3,
            color=(0, 255, 0, 255),
            thickness=self.outline_thickness,
            parent=self.canvas,
        )

    def draw_point(self, p: Vec2, size: float, color: Color):
        screen_pos = round(self.view_transform(p)).as_tuple
        dpg.draw_circle(
            center=screen_pos,
            radius=max(1, size),
            fill=tuple(color),
            thickness=0,
            parent=self.canvas,
        )

    def draw_solid_capsule(self, p1: Vec2, p2: Vec2, radius: float, color: Color):
        sp1 = tuple(round(self.view_transform(p1)))
        sp2 = tuple(round(self.view_transform(p2)))
        sr = max(1, round(radius * abs(self.view_transform._scale.x)))
        # Calculate the perpendicular direction in screen space.
        diff = Vec2(sp2[0] - sp1[0], sp2[1] - sp1[1])
        length = diff.length
        perp = diff.perpendicular("right").normalize() if length != 0 else Vec2.zero()
        offset = perp * sr
        p1_plus = (sp1[0] + round(offset.x), sp1[1] + round(offset.y))
        p1_minus = (sp1[0] - round(offset.x), sp1[1] - round(offset.y))
        p2_plus = (sp2[0] + round(offset.x), sp2[1] + round(offset.y))
        p2_minus = (sp2[0] - round(offset.x), sp2[1] - round(offset.y))
        fill_color = tuple(color)
        dpg.draw_polygon(
            [p1_plus, p2_plus, p2_minus, p1_minus],
            fill=fill_color,
            thickness=0,
            parent=self.canvas,
        )
        dpg.draw_circle(
            center=sp1, radius=sr, fill=fill_color, thickness=0, parent=self.canvas
        )
        dpg.draw_circle(
            center=sp2, radius=sr, fill=fill_color, thickness=0, parent=self.canvas
        )
        outline_color = tuple(min(255, c + 50) for c in (color.r, color.g, color.b))
        outline_color += (255,)
        dpg.draw_polyline(
            [p1_plus, p2_plus, p2_minus, p1_minus],
            color=outline_color,
            thickness=self.outline_thickness,
            closed=True,
            parent=self.canvas,
        )
        dpg.draw_circle(
            center=sp1,
            radius=sr,
            color=outline_color,
            thickness=self.outline_thickness,
            parent=self.canvas,
        )
        dpg.draw_circle(
            center=sp2,
            radius=sr,
            color=outline_color,
            thickness=self.outline_thickness,
            parent=self.canvas,
        )
