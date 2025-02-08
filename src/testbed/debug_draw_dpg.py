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

    def draw_solid_polygon(self, transform, vertices, radius, color: Color):
        # The vertices are specified in local coordinates. Apply the transform:
        transformed = []
        # Calculate the angle from the rotation component.
        angle = math.atan2(transform.q.s, transform.q.c)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        for v in vertices:
            x = transform.p.x + (v.x * cos_a - v.y * sin_a)
            y = transform.p.y + (v.x * sin_a + v.y * cos_a)
            transformed.append(Vec2(x, y))
        points = [self.world_to_screen(v) for v in transformed]
        
        #fill_color = self._to_color(color)
        dpg.draw_polygon(points,
                         fill=tuple(color),
                         color=tuple(color),
                         parent=self.canvas)
        # Draw the outline using a slightly brighter color.
        outline_color = (min(255, color.r + 50),
                         min(255, color.g + 50),
                         min(255, color.b + 50),
                         255)
        dpg.draw_polyline(points,
                          color=outline_color,
                          thickness=self.outline_thickness,
                          closed=True,
                          parent=self.canvas)

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
