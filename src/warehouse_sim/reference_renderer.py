"""Render the V2 reference layout with pygame or Pillow."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple

from .facility_layout import FacilityLayout
from .lane_graph import LaneGraph
from .motion import MotionEngine
from .render_plan import DrawCommand, Primitive, build_render_plan


def _scaled_rect(points, sx, sy, ox=0, oy=0):
    x, y, width, height = points
    return (round(ox + x * sx), round(oy + y * sy), max(1, round(width * sx)), max(1, round(height * sy)))


def motion_render_plan(engine: MotionEngine) -> tuple[DrawCommand, ...]:
    commands = []
    for entity in engine.entities:
        x, y = entity.position(engine.graph)
        points = (x - entity.width / 2, y - entity.height / 2, entity.width, entity.height)
        primitive = {
            "rectangle": Primitive.RECT,
            "circle": Primitive.CIRCLE,
            "diamond": Primitive.DIAMOND,
        }[entity.shape.value]
        commands.append(DrawCommand(primitive, points, entity.color, outline=(65, 65, 65)))
    return tuple(commands)


def _draw_pillow_commands(draw, commands, sx, sy) -> None:
    for command in commands:
        if command.primitive == Primitive.RECT:
            x, y, width, height = _scaled_rect(command.points, sx, sy)
            draw.rectangle((x, y, x + width, y + height), fill=command.fill, outline=command.outline)
        elif command.primitive == Primitive.LINE:
            x1, y1, x2, y2 = command.points
            draw.line((x1 * sx, y1 * sy, x2 * sx, y2 * sy), fill=command.fill, width=max(1, round(command.width * min(sx, sy))))
        elif command.primitive == Primitive.CIRCLE:
            x, y, width, height = _scaled_rect(command.points, sx, sy)
            draw.ellipse((x, y, x + width, y + height), fill=command.fill, outline=command.outline)
        elif command.primitive == Primitive.DIAMOND:
            x, y, width, height = _scaled_rect(command.points, sx, sy)
            draw.polygon(((x + width // 2, y), (x + width, y + height // 2), (x + width // 2, y + height), (x, y + height // 2)), fill=command.fill, outline=command.outline)


def render_with_pillow(layout: FacilityLayout, output: Path, size=(1280, 720)) -> Path:
    """Create deterministic visual evidence without requiring a display."""
    from PIL import Image, ImageDraw

    image = Image.new("RGB", size, (30, 30, 30))
    draw = ImageDraw.Draw(image)
    sx, sy = size[0] / layout.design_width, size[1] / layout.design_height
    _draw_pillow_commands(draw, build_render_plan(layout), sx, sy)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    return output


def render_motion_with_pillow(layout: FacilityLayout, engine: MotionEngine, output: Path, size=(1280, 720)) -> Path:
    """Render a V3 motion snapshot from the same graph used by simulation."""
    from PIL import Image, ImageDraw

    image = Image.new("RGB", size, (30, 30, 30))
    draw = ImageDraw.Draw(image)
    sx, sy = size[0] / layout.design_width, size[1] / layout.design_height
    base = build_render_plan(layout, engine.graph.network_segments(), include_entities=False)
    _draw_pillow_commands(draw, base, sx, sy)
    _draw_pillow_commands(draw, motion_render_plan(engine), sx, sy)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    return output


class ReferenceLayoutUI:
    """Small pygame shell around the backend-neutral V2 render plan."""

    def __init__(
        self,
        layout: FacilityLayout,
        graph: LaneGraph | None = None,
        engine: MotionEngine | None = None,
        size=(1280, 720),
    ) -> None:
        import pygame

        self.pygame = pygame
        pygame.init()
        self.layout = layout
        self.size = size
        self.screen = pygame.display.set_mode(size, pygame.RESIZABLE)
        pygame.display.set_caption("Warehouse Reference Layout - V2")
        self.clock = pygame.time.Clock()
        self.graph = graph
        self.engine = engine
        network = graph.network_segments() if graph is not None else None
        self.plan = build_render_plan(layout, network, include_entities=engine is None)
        self.show_nodes = False
        self.show_routes = False

    def _viewport(self):
        width, height = self.screen.get_size()
        scale = min(width / self.layout.design_width, height / self.layout.design_height)
        render_width = self.layout.design_width * scale
        render_height = self.layout.design_height * scale
        return scale, (width - render_width) / 2, (height - render_height) / 2

    def draw(self) -> None:
        pygame = self.pygame
        self.screen.fill((28, 28, 28))
        scale, ox, oy = self._viewport()
        commands = list(self.plan)
        if self.show_routes and self.engine is not None:
            for entity in self.engine.entities:
                for source_id, target_id in zip(entity.route, entity.route[1:]):
                    source = self.graph.node(source_id)
                    target = self.graph.node(target_id)
                    commands.append(DrawCommand(Primitive.LINE, (source.x, source.y, target.x, target.y), entity.color, 2.5))
        if self.engine is not None:
            commands.extend(motion_render_plan(self.engine))
        for command in commands:
            if command.primitive == Primitive.RECT:
                rect = pygame.Rect(_scaled_rect(command.points, scale, scale, ox, oy))
                pygame.draw.rect(self.screen, command.fill, rect)
                if command.outline:
                    pygame.draw.rect(self.screen, command.outline, rect, 1)
            elif command.primitive == Primitive.LINE:
                x1, y1, x2, y2 = command.points
                pygame.draw.line(self.screen, command.fill, (round(ox + x1 * scale), round(oy + y1 * scale)), (round(ox + x2 * scale), round(oy + y2 * scale)), max(1, round(command.width * scale)))
            elif command.primitive == Primitive.CIRCLE:
                x, y, width, height = _scaled_rect(command.points, scale, scale, ox, oy)
                pygame.draw.ellipse(self.screen, command.fill, pygame.Rect(x, y, width, height))
            elif command.primitive == Primitive.DIAMOND:
                x, y, width, height = _scaled_rect(command.points, scale, scale, ox, oy)
                polygon = ((x + width // 2, y), (x + width, y + height // 2), (x + width // 2, y + height), (x, y + height // 2))
                pygame.draw.polygon(self.screen, command.fill, polygon)
                if command.outline:
                    pygame.draw.polygon(self.screen, command.outline, polygon, 1)
        if self.show_nodes and self.graph is not None:
            for node in self.graph.nodes:
                pygame.draw.circle(self.screen, (80, 80, 80), (round(ox + node.x * scale), round(oy + node.y * scale)), max(1, round(2 * scale)))
        pygame.display.flip()

    def run(self) -> None:
        active = True
        while active:
            delta_time = min(self.clock.tick(60) / 1000.0, 0.1)
            for event in self.pygame.event.get():
                if event.type == self.pygame.QUIT:
                    active = False
                elif event.type == self.pygame.KEYDOWN and event.key in (self.pygame.K_ESCAPE, self.pygame.K_q):
                    active = False
                elif event.type == self.pygame.KEYDOWN and self.engine is not None:
                    if event.key == self.pygame.K_SPACE:
                        self.engine.pause() if self.engine.running else self.engine.start()
                    elif event.key == self.pygame.K_r:
                        self.engine.reset()
                    elif event.key == self.pygame.K_n:
                        self.show_nodes = not self.show_nodes
                    elif event.key == self.pygame.K_p:
                        self.show_routes = not self.show_routes
            if self.engine is not None:
                self.engine.update(delta_time)
            self.draw()
        self.pygame.quit()
