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
        self.outline_thickness = 1.5  # use thicker outlines, if desired

        self.view_transform = ScaledTransform(
            position=(400, 300),
            rotation=0,
            scale=(30, -30)
        )

    def world_to_screen(self, pos: Vec2):
        """
        Convert a Box2D world coordinate (Vec2) to screen coordinates
        using the current view transform.
        """
        screen_point = self.view_transform(pos)
        return (round(screen_point.x), round(screen_point.y))

    def draw_polygon(self, vertices: list[Vec2], color: Color):
        if len(vertices) < 2:
            return
        points = [self.world_to_screen(v) for v in vertices]
        points.append(points[0])
        dpg.draw_polygon(points,
                         color=tuple(color),
                         thickness=self.outline_thickness,
                         parent=self.canvas)

    def draw_rounded_polygon(self, transform, vertices, radius, color: "Color"):
        """
        Draws a filled polygon expanded by 'radius' (i.e. the Minkowski sum of the polygon and
        a disc of the given radius). For each vertex of the transformed polygon, two tangent
        points are computed by offsetting the vertex along the outward normals of its incident edges.
        Then instead of simply taking the smaller angular difference, we choose the arc (between the two
        tangent points) whose midpoint is closest to the average outward direction. This ensures that
        the arc always stays on the outside of the polygon.
        
        (Make sure that your polygon vertices are specified in counterclockwise order.)
        """
        import math

        # First, transform local vertices into world coordinates.
        world_vertices = []
        a = math.atan2(transform.q.s, transform.q.c)
        cos_a = math.cos(a)
        sin_a = math.sin(a)
        for v in vertices:
            x = transform.p.x + (v.x * cos_a - v.y * sin_a)
            y = transform.p.y + (v.x * sin_a + v.y * cos_a)
            world_vertices.append(Vec2(x, y))

        n = len(world_vertices)
        arc_segments = 8  # number of segments for each rounded corner
        outline_points = []

        # Helper for angle difference (in range [-pi, pi])
        def angle_diff(a, b):
            diff = (a - b) % (2 * math.pi)
            if diff > math.pi:
                diff -= 2 * math.pi
            return diff

        # Process each vertex.
        for i in range(n):
            v = world_vertices[i]
            prev = world_vertices[i - 1]             # note: Python negative index wraps
            nxt = world_vertices[(i + 1) % n]

            # Compute outward normals for the two incident edges.
            # For a CCW polygon, the outward normal is given by a clockwise rotation.
            d_curr = Vec2(nxt.x - v.x, nxt.y - v.y)
            len_d = math.hypot(d_curr.x, d_curr.y) or 1.0
            d_curr_norm = Vec2(d_curr.x / len_d, d_curr.y / len_d)
            n_curr = Vec2(d_curr_norm.y, -d_curr_norm.x)

            d_prev = Vec2(v.x - prev.x, v.y - prev.y)
            len_d_prev = math.hypot(d_prev.x, d_prev.y) or 1.0
            d_prev_norm = Vec2(d_prev.x / len_d_prev, d_prev.y / len_d_prev)
            n_prev = Vec2(d_prev_norm.y, -d_prev_norm.x)

            # Compute the two tangent points (the offset points).
            pt_prev = Vec2(v.x + radius * n_prev.x, v.y + radius * n_prev.y)
            pt_curr = Vec2(v.x + radius * n_curr.x, v.y + radius * n_curr.y)

            # Compute the angles (in [0, 2pi)) of these offsets relative to the vertex.
            a_prev = math.atan2(pt_prev.y - v.y, pt_prev.x - v.x) % (2 * math.pi)
            a_curr = math.atan2(pt_curr.y - v.y, pt_curr.x - v.x) % (2 * math.pi)

            # Compute the average outward direction from the two normals.
            avg_out_x = n_prev.x + n_curr.x
            avg_out_y = n_prev.y + n_curr.y
            avg_angle = math.atan2(avg_out_y, avg_out_x) % (2 * math.pi)

            # Create two candidate arcs:
            # Candidate 1: from a_prev to a_curr (positive direction)
            candidate1 = (a_curr - a_prev) % (2 * math.pi)
            mid1 = (a_prev + candidate1 / 2) % (2 * math.pi)
            # Candidate 2: from a_curr to a_prev (positive direction)
            candidate2 = (a_prev - a_curr) % (2 * math.pi)
            mid2 = (a_curr + candidate2 / 2) % (2 * math.pi)

            # Choose the candidate whose midpoint is closer to the average outward direction.
            if abs(angle_diff(mid1, avg_angle)) <= abs(angle_diff(mid2, avg_angle)):
                start_angle = a_prev
                end_angle = a_curr
                sweep = candidate1
            else:
                start_angle = a_curr
                end_angle = a_prev
                sweep = candidate2

            # Ensure the sweep goes in the correct (increasing) direction.
            if end_angle < start_angle:
                end_angle += 2 * math.pi

            # (Optional) If the sweep is larger than 180°, switch to the complementary arc.
            # For an expanded polygon, the desired arc is the one on the outside.
            if sweep > math.pi:
                # Complement the arc.
                # Swap the endpoints so the sweep becomes 2pi - sweep.
                start_angle, end_angle = end_angle, start_angle + 2 * math.pi
                sweep = 2 * math.pi - sweep

            # Sample points along the chosen arc.
            corner_points = []
            for j in range(arc_segments + 1):
                t = j / arc_segments
                angle_now = start_angle + t * (end_angle - start_angle)
                arc_pt = Vec2(v.x + radius * math.cos(angle_now),
                              v.y + radius * math.sin(angle_now))
                corner_points.append(self.world_to_screen(arc_pt))

            # Append the arc's points to the outline.
            # Skip the first point if it's not the first vertex to avoid duplicates.
            if i == 0:
                outline_points.extend(corner_points)
            else:
                outline_points.extend(corner_points[1:])

        # Finally, draw the filled, expanded polygon.
        dpg.draw_polygon(outline_points,
                         fill=tuple(color)[:3] + (150,),
                         color=tuple(color),
                         parent=self.canvas)

    
    def draw_solid_polygon(self, transform, vertices, radius, color: Color):
        """
        Draws a solid polygon. If 'radius' is nonzero,
        calls draw_rounded_polygon to draw a rounded polygon;
        otherwise, it uses the normal polygon drawing.
        """
        if radius != 0:
            self.draw_rounded_polygon(transform, vertices, radius, color)
            return

        # Fallback: normal solid polygon drawing.
        transformed = []
        angle = math.atan2(transform.q.s, transform.q.c)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        # Append the first vertex at the end to close the polygon.
        vertices.append(vertices[0])
        for v in vertices:
            x = transform.p.x + (v.x * cos_a - v.y * sin_a)
            y = transform.p.y + (v.x * sin_a + v.y * cos_a)
            transformed.append(Vec2(x, y))
        points = [self.world_to_screen(v) for v in transformed]
        line_color = (min(255, color.r + 100),
                      min(255, color.g + 100),
                      min(255, color.b + 100),
                      255)
        dpg.draw_polygon(points,
                         fill=tuple(color)[:3] + (150,),
                         color=tuple(line_color),
                         parent=self.canvas)
        # Draw the outline using a slightly brighter color.
        #outline_color = (tuple(color))
        #dpg.draw_polyline(points,
        #                  color=tuple(color),
        #                  thickness=self.outline_thickness,
        #                  closed=True,
        #                  parent=self.canvas)


    def draw_string(self, p: Vec2, s, color: Color):
        pos = self.world_to_screen(p)
        dpg.draw_text(pos, s,
                      color=tuple(color),
                      size=14,
                      parent=self.canvas)

    def draw_circle(self, center: Vec2, radius: float, color: Color):
        center_screen = self.world_to_screen(center)
        # Use the x–scale as conversion factor (take its absolute value)
        scaled_radius = round(radius * abs(self.view_transform._scale.x))
        dpg.draw_circle(center=center_screen,
                        radius=scaled_radius,
                        color=tuple(color),
                        thickness=self.outline_thickness,
                        parent=self.canvas)

    def draw_solid_circle(self, transform, radius, color: Color):
        center = transform.p
        angle = math.atan2(transform.q.s, transform.q.c)
        center_screen = self.world_to_screen(center)
        scaled_radius = round(radius * abs(self.view_transform._scale.x))
        fill_color = tuple(color)
        dpg.draw_circle(center=center_screen,
                        radius=scaled_radius,
                        fill=fill_color,
                        thickness=0,
                        parent=self.canvas)
        # Draw the orientation line.
        edge_x = center_screen[0] + round(scaled_radius * math.cos(angle))
        edge_y = center_screen[1] - round(scaled_radius * math.sin(angle))
        line_color = (min(255, color.r + 100),
                      min(255, color.g + 100),
                      min(255, color.b + 100),
                      255)
        dpg.draw_line(center_screen, (edge_x, edge_y),
                      color=line_color,
                      thickness=self.outline_thickness,
                      parent=self.canvas)

        # Outline the circle.
        outline_color = (min(255, color.r + 50),
                         min(255, color.g + 50),
                         min(255, color.b + 50),
                         255)
        dpg.draw_circle(center=center_screen,
                        radius=scaled_radius,
                        color=outline_color,
                        thickness=self.outline_thickness,
                        parent=self.canvas)

    def draw_segment(self, p1: Vec2, p2: Vec2, color: Color):
        sp1 = self.world_to_screen(p1)
        sp2 = self.world_to_screen(p2)
        dpg.draw_line(sp1, sp2,
                      color=tuple(color),
                      thickness=self.outline_thickness,
                      parent=self.canvas)

    def draw_transform(self, transform):
        p = transform.p
        angle = math.atan2(transform.q.s, transform.q.c)
        # x–axis and y–axis derived from the rotation.
        x_axis = Vec2(math.cos(angle), math.sin(angle))
        y_axis = Vec2(-math.sin(angle), math.cos(angle))
        p1 = p
        p2 = Vec2(p.x + x_axis.x, p.y + x_axis.y)
        p3 = Vec2(p.x + y_axis.x, p.y + y_axis.y)
        sp1 = self.world_to_screen(p1)
        sp2 = self.world_to_screen(p2)
        sp3 = self.world_to_screen(p3)
        dpg.draw_line(sp1, sp2,
                      color=(255, 0, 0, 255),
                      thickness=self.outline_thickness,
                      parent=self.canvas)
        dpg.draw_line(sp1, sp3,
                      color=(0, 255, 0, 255),
                      thickness=self.outline_thickness,
                      parent=self.canvas)

    def draw_point(self, p: Vec2, size: float, color: Color):
        center_screen = self.world_to_screen(p)
        scaled_size = max(1, round(size * self.view_transform._scale.x))
        radius = 3
        dpg.draw_circle(center=center_screen,
                        radius=radius,
                        fill=tuple(color),
                        thickness=0,
                        parent=self.canvas)

    def draw_solid_capsule(self, p1: Vec2, p2: Vec2, radius: float, color: Color):
        sp1 = self.world_to_screen(p1)
        sp2 = self.world_to_screen(p2)
        sr = max(1, round(radius * abs(self.view_transform._scale.x)))
        dx = sp2[0] - sp1[0]
        dy = sp2[1] - sp1[1]

        length = math.hypot(dx, dy)
        perp_x = -dy / length
        perp_y = dx / length
        offset_x = round(perp_x * sr)
        offset_y = round(perp_y * sr)
        p1_plus  = (sp1[0] + offset_x, sp1[1] + offset_y)
        p1_minus = (sp1[0] - offset_x, sp1[1] - offset_y)
        p2_plus  = (sp2[0] + offset_x, sp2[1] + offset_y)
        p2_minus = (sp2[0] - offset_x, sp2[1] - offset_y)
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
        outline_color = (min(255, color.r + 50),
                         min(255, color.g + 50),
                         min(255, color.b + 50),
                         255)
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
