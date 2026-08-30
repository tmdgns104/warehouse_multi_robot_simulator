"""Render the V2 reference layout with pygame or Pillow."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple

from .facility_layout import FacilityLayout, NetworkSegment
from .lane_graph import LaneGraph
from .motion import MotionEngine, MotionState
from .render_plan import DrawCommand, Primitive, build_render_plan
from .task_manager import RobotWorkState
from .lane_safety import (
    driving_obstacles,
    machine_obstacles,
    reference_render_segments,
    reference_visual_only_segments,
    station_obstacles,
)


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
        outline = (220, 38, 38) if entity.state == MotionState.WAITING else (65, 65, 65)
        commands.append(DrawCommand(primitive, points, entity.color, width=2 if entity.state == MotionState.WAITING else 1, outline=outline))
    return tuple(commands)


def factory_status_render_plan(engine) -> tuple[DrawCommand, ...]:
    """Small robot-local markers that preserve the reference visual scale."""
    if not hasattr(engine, "work_states"):
        return ()
    commands = []
    for entity in engine.entities:
        state = engine.work_states[entity.id]
        x, y = entity.position(engine.graph)
        if state in (RobotWorkState.CARRYING, RobotWorkState.TO_DESTINATION_STAGING,
                     RobotWorkState.WAITING_DESTINATION):
            commands.append(DrawCommand(Primitive.RECT, (x - 2.5, y - 2.5, 5, 5), (250, 224, 82), outline=(78, 63, 28)))
        elif state in (RobotWorkState.PICKING, RobotWorkState.DROPPING):
            color = (245, 157, 52) if state == RobotWorkState.PICKING else (150, 79, 190)
            commands.append(DrawCommand(Primitive.CIRCLE, (x - 6.5, y - 6.5, 13, 13), color, outline=(55, 55, 55)))
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
    base = build_render_plan(
        layout, reference_render_segments(layout, engine.graph), include_entities=False
    )
    _draw_pillow_commands(draw, base, sx, sy)
    _draw_pillow_commands(draw, motion_render_plan(engine), sx, sy)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    return output


def render_factory_with_pillow(layout: FacilityLayout, engine, output: Path, size=(1280, 720), debug=False) -> Path:
    """Render task-driven V5 evidence including compact metrics and load state."""
    from PIL import Image, ImageDraw

    image = Image.new("RGB", size, (30, 30, 30))
    draw = ImageDraw.Draw(image)
    sx, sy = size[0] / layout.design_width, size[1] / layout.design_height
    base = build_render_plan(layout, reference_render_segments(layout, engine.graph), False)
    _draw_pillow_commands(draw, base, sx, sy)
    _draw_pillow_commands(draw, motion_render_plan(engine), sx, sy)
    _draw_pillow_commands(draw, factory_status_render_plan(engine), sx, sy)
    metrics = engine.factory_metrics
    lines = (
        "V5.2 FACTORY FLOW",
        f"QUEUE       {metrics.tasks_queued}",
        f"ACTIVE      {metrics.tasks_active}",
        f"COMPLETED   {metrics.tasks_completed}",
        f"PRODUCTIVE  {metrics.productive_utilization * 100:4.1f}%",
        f"TASK WAIT   {metrics.task_waiting_ratio * 100:4.1f}%",
        f"ENGAGED     {metrics.engaged_ratio * 100:4.1f}%",
        f"TRUE IDLE   {metrics.true_idle_robot_count}",
        f"LOADS MOVE  {metrics.loads_in_transit}",
    )
    for index, line in enumerate(lines):
        draw.text((995, 74 + index * 18), line, fill=(35, 35, 35))
    robot_y = 250
    for entity in engine.entities[:16]:
        task_id = engine.robot_tasks[entity.id] or "-"
        text = f"{entity.id} {engine.work_states[entity.id].value:<10} {task_id}"
        draw.text((995, robot_y), text, fill=(45, 45, 45))
        robot_y += 16
    if debug:
        for station in engine.stations.values():
            node = engine.graph.node(station.service_node_id)
            radius = 4
            draw.ellipse((node.x - radius, node.y - radius, node.x + radius, node.y + radius), fill=(255, 165, 0), outline=(50, 50, 50))
            draw.text((node.x + 6, node.y - 9), station.id, fill=(35, 35, 35))
            for staging_id in station.staging_node_ids:
                staging = engine.graph.node(staging_id)
                draw.rectangle((staging.x - 3, staging.y - 3, staging.x + 3, staging.y + 3),
                               fill=(40, 125, 190), outline=(30, 50, 70))
        debug_lines = (
            f"DIRECT HANDOFF {metrics.direct_task_handoffs}",
            f"PARK RETURNS   {metrics.parking_returns}",
            f"BLOCK SOURCE   {metrics.assignment_blocked_source_station}",
            f"BLOCK DEST     {metrics.assignment_blocked_destination_station}",
            f"BLOCK LIMIT    {metrics.assignment_blocked_max_active}",
            f"BLOCK NO IDLE  {metrics.assignment_blocked_no_idle_robot}",
            f"BLOCK NO ROUTE {metrics.assignment_blocked_no_route}",
            f"STAGING BLOCK  {metrics.staging_capacity_blocks}",
            f"LATE SERVICE   {metrics.late_service_reservations}",
        )
        for index, line in enumerate(debug_lines):
            draw.text((995, 520 + index * 17), line, fill=(75, 40, 40))
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
        pygame.display.set_caption(
            "Warehouse Multi-Robot Factory - V5.2" if engine is not None and hasattr(engine, "factory_metrics")
            else "Warehouse Multi-Robot Traffic - V4"
        )
        self.clock = pygame.time.Clock()
        self.graph = graph
        self.engine = engine
        network = reference_render_segments(layout, graph) if graph is not None else None
        self.plan = build_render_plan(layout, network, include_entities=engine is None)
        self.show_nodes = False
        self.show_routes = False
        self.show_reservations = False
        self.show_entity_ids = False
        self.show_topology_debug = False

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
            commands.extend(factory_status_render_plan(self.engine))
        if self.show_reservations and self.engine is not None and hasattr(self.engine, "controller"):
            controller = self.engine.controller
            for edge_id in controller.edge_reservations:
                edge = self.graph.edge(edge_id)
                source, target = self.graph.node(edge.source), self.graph.node(edge.target)
                commands.append(DrawCommand(Primitive.LINE, (source.x, source.y, target.x, target.y), (231, 76, 60), 3.0))
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
        if self.show_entity_ids and self.engine is not None:
            font = pygame.font.SysFont("arial", max(9, round(11 * scale)))
            for entity in self.engine.entities:
                x, y = entity.position(self.graph)
                label = font.render(entity.id, True, (35, 35, 35))
                self.screen.blit(label, (round(ox + x * scale + 7), round(oy + y * scale - 8)))
        if self.show_topology_debug and self.graph is not None:
            for obstacle in driving_obstacles(self.layout):
                expanded = pygame.Rect(_scaled_rect(
                    (obstacle.left, obstacle.top, obstacle.right - obstacle.left, obstacle.bottom - obstacle.top),
                    scale, scale, ox, oy,
                ))
                pygame.draw.rect(self.screen, (220, 45, 45), expanded, max(1, round(scale)))
            for machine in self.layout.machines:
                bounds = pygame.Rect(_scaled_rect(
                    (machine.x, machine.y, machine.width, machine.height), scale, scale, ox, oy
                ))
                pygame.draw.rect(self.screen, (235, 151, 35), bounds, max(1, round(2 * scale)))
            for station in self.layout.stations:
                bounds = pygame.Rect(_scaled_rect(
                    (station.x, station.y, station.width, station.height), scale, scale, ox, oy
                ))
                pygame.draw.rect(self.screen, (135, 75, 175), bounds, max(1, round(2 * scale)))
            for node in self.graph.nodes:
                pygame.draw.circle(
                    self.screen, (25, 95, 70),
                    (round(ox + node.x * scale), round(oy + node.y * scale)),
                    max(2, round(2 * scale)),
                )
        if self.engine is not None and hasattr(self.engine, "factory_metrics"):
            font = pygame.font.SysFont("consolas", max(9, round(12 * scale)))
            metrics = self.engine.factory_metrics
            panel_lines = (
                "V5.2 FACTORY FLOW",
                f"QUEUE       {metrics.tasks_queued}",
                f"ACTIVE      {metrics.tasks_active}",
                f"COMPLETED   {metrics.tasks_completed}",
                f"PRODUCTIVE  {metrics.productive_utilization * 100:4.1f}%",
                f"TASK WAIT   {metrics.task_waiting_ratio * 100:4.1f}%",
                f"ENGAGED     {metrics.engaged_ratio * 100:4.1f}%",
                f"TRUE IDLE   {metrics.true_idle_robot_count}",
                f"LOADS MOVE  {metrics.loads_in_transit}",
            )
            panel_x = round(ox + 990 * scale)
            panel_y = round(oy + 72 * scale)
            for index, line in enumerate(panel_lines):
                label = font.render(line, True, (35, 35, 35))
                self.screen.blit(label, (panel_x, panel_y + index * max(14, round(18 * scale))))
            robot_y = panel_y + max(160, round(180 * scale))
            for entity in self.engine.entities[:16]:
                task_id = self.engine.robot_tasks[entity.id] or "-"
                line = f"{entity.id} {self.engine.work_states[entity.id].value:<10} {task_id}"
                label = font.render(line, True, (45, 45, 45))
                self.screen.blit(label, (panel_x, robot_y))
                robot_y += max(12, round(16 * scale))
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
                    elif event.key == self.pygame.K_t:
                        self.show_reservations = not self.show_reservations
                    elif event.key == self.pygame.K_i:
                        self.show_entity_ids = not self.show_entity_ids
                    elif event.key == self.pygame.K_d:
                        self.show_topology_debug = not self.show_topology_debug
            if self.engine is not None:
                self.engine.update(delta_time)
            self.draw()
        self.pygame.quit()


def render_topology_debug_with_pillow(layout: FacilityLayout, graph: LaneGraph, output: Path, size=(1280, 720)) -> Path:
    """Render expanded obstacles, safe edges, and nodes for review evidence."""
    from PIL import Image, ImageDraw

    image = Image.new("RGB", size, (30, 30, 30))
    draw = ImageDraw.Draw(image, "RGBA")
    sx, sy = size[0] / layout.design_width, size[1] / layout.design_height
    visual_only = reference_visual_only_segments(layout)
    component_by_node = {}
    remaining = {node.id for node in graph.nodes}
    component = 0
    while remaining:
        component += 1
        start = min(remaining)
        remaining.remove(start)
        stack = [start]
        component_by_node[start] = component
        while stack:
            for neighbor in graph.neighbors(stack.pop()):
                if neighbor.id in remaining:
                    remaining.remove(neighbor.id)
                    component_by_node[neighbor.id] = component
                    stack.append(neighbor.id)
    component_colors = ((35, 150, 112), (78, 111, 207), (171, 102, 204))
    debug_driving = tuple(
        NetworkSegment(
            f"debug_{edge.id}",
            graph.node(edge.source).position,
            graph.node(edge.target).position,
            component_colors[(component_by_node[edge.source] - 1) % len(component_colors)],
            2.0,
        )
        for edge in graph.edges
    )
    _draw_pillow_commands(
        draw,
        build_render_plan(layout, (*debug_driving, *visual_only), False),
        sx,
        sy,
    )
    for obstacle in driving_obstacles(layout):
        draw.rectangle(
            (obstacle.left * sx, obstacle.top * sy, obstacle.right * sx, obstacle.bottom * sy),
            outline=(230, 40, 40, 230),
            fill=(230, 40, 40, 35),
            width=1,
        )
    for machine in layout.machines:
        draw.rectangle(
            (machine.x * sx, machine.y * sy, (machine.x + machine.width) * sx, (machine.y + machine.height) * sy),
            outline=(235, 151, 35, 255),
            width=2,
        )
    for station in layout.stations:
        draw.rectangle(
            (station.x * sx, station.y * sy, (station.x + station.width) * sx, (station.y + station.height) * sy),
            outline=(135, 75, 175, 255),
            width=2,
        )
    for node in graph.nodes:
        radius = 2
        draw.ellipse(
            (node.x * sx - radius, node.y * sy - radius, node.x * sx + radius, node.y * sy + radius),
            fill=(30, 30, 30, 220),
        )
    legend_x, legend_y = 995, 82
    draw.text((legend_x, legend_y), "DEBUG TOPOLOGY", fill=(30, 30, 30, 255))
    draw.line((legend_x, legend_y + 22, legend_x + 28, legend_y + 22), fill=(35, 150, 112, 255), width=3)
    draw.text((legend_x + 36, legend_y + 15), "driving lane / component 1", fill=(30, 30, 30, 255))
    draw.line((legend_x, legend_y + 42, legend_x + 28, legend_y + 42), fill=(172, 187, 196, 255), width=2)
    draw.text((legend_x + 36, legend_y + 35), "visual-only", fill=(30, 30, 30, 255))
    draw.rectangle((legend_x, legend_y + 56, legend_x + 28, legend_y + 70), outline=(235, 151, 35, 255), width=2)
    draw.text((legend_x + 36, legend_y + 55), "machine bounds", fill=(30, 30, 30, 255))
    draw.rectangle((legend_x, legend_y + 77, legend_x + 28, legend_y + 91), outline=(230, 40, 40, 255), width=1)
    draw.text((legend_x + 36, legend_y + 76), "7 px clearance", fill=(30, 30, 30, 255))
    draw.rectangle((legend_x, legend_y + 98, legend_x + 28, legend_y + 112), outline=(135, 75, 175, 255), width=2)
    draw.text((legend_x + 36, legend_y + 97), "station bounds", fill=(30, 30, 30, 255))
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    return output
