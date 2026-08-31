"""Render the V2 reference layout with pygame or Pillow."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple

from .facility_layout import FacilityLayout, NetworkSegment
from .factory import PhysicalActivity
from .lane_graph import LaneGraph
from .motion import MotionEngine, MotionState
from .mission_view import MISSION_COLORS, mission_counts, robot_mission_view
from .warehouse_view import WAREHOUSE_LOCATION_ANCHORS, warehouse_box_views, warehouse_robot_view
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


def _production_robot_line(engine, entity) -> str:
    view = robot_mission_view(engine, entity.id)
    if not view.mission:
        return f"{entity.id} TRUE_IDLE"
    cargo = " BOX" if view.has_cargo else ""
    activity = view.operational_state.replace("RESOURCE_WAIT", "RES_WAIT")
    return (f"{entity.id} {activity:<8} | {view.mission:<6}{cargo} "
            f"{view.lot_id[-4:]} {view.source}>{view.destination}")


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


def render_factory_with_pillow(layout: FacilityLayout, engine, output: Path, size=(1280, 720),
                               debug=False, selected_robot_id: str | None = None) -> Path:
    """Render task-driven V5 evidence including compact metrics and load state."""
    from PIL import Image, ImageDraw

    image = Image.new("RGB", size, (30, 30, 30))
    draw = ImageDraw.Draw(image)
    sx, sy = size[0] / layout.design_width, size[1] / layout.design_height
    base = build_render_plan(layout, reference_render_segments(layout, engine.graph), False)
    _draw_pillow_commands(draw, base, sx, sy)
    _draw_pillow_commands(draw, motion_render_plan(engine), sx, sy)
    _draw_pillow_commands(draw, factory_status_render_plan(engine), sx, sy)
    is_production = hasattr(engine, "production_metrics")
    if is_production:
        for entity in engine.entities:
            view = robot_mission_view(engine, entity.id)
            if not view.mission:
                continue
            x, y = entity.position(engine.graph)
            color = MISSION_COLORS[view.mission]
            draw.rounded_rectangle((x * sx + 5, y * sy - 16, x * sx + 43, y * sy - 1),
                                   radius=3, fill=(255, 255, 255), outline=color, width=2)
            draw.text((x * sx + 8, y * sy - 15), f"{entity.id} {view.mission[:3]}", fill=color)
        if selected_robot_id:
            selected = robot_mission_view(engine, selected_robot_id)
            for first, second in zip(selected.route_node_ids, selected.route_node_ids[1:]):
                a, b = engine.graph.node(first), engine.graph.node(second)
                draw.line((a.x * sx, a.y * sy, b.x * sx, b.y * sy), fill=(20, 105, 215), width=4)
            for node_id, label, color in ((selected.source_node_id, "S", (28, 135, 72)),
                                          (selected.destination_node_id, "D", (190, 55, 55))):
                if node_id:
                    node = engine.graph.node(node_id)
                    draw.ellipse((node.x * sx - 8, node.y * sy - 8, node.x * sx + 8, node.y * sy + 8),
                                 fill=(255, 255, 255), outline=color, width=3)
                    draw.text((node.x * sx - 3, node.y * sy - 7), label, fill=color)
    metrics = engine.factory_metrics
    activity_counts = {activity: sum(value == activity for value in engine.activity_states.values())
                       for activity in PhysicalActivity}
    lines = (
        "V5.3 ACTUAL FACTORY FLOW",
        f"MOVE {activity_counts[PhysicalActivity.ACTUALLY_MOVING]:2d}  SERVICE {activity_counts[PhysicalActivity.SERVICING]:2d}",
        f"TRAFFIC WAIT {activity_counts[PhysicalActivity.TRAFFIC_WAIT]:2d}",
        f"RESOURCE WAIT {activity_counts[PhysicalActivity.RESOURCE_WAIT]:2d}",
        f"HOLD {activity_counts[PhysicalActivity.HOLDING]:2d}  IDLE {activity_counts[PhysicalActivity.TRUE_IDLE]:2d}",
        f"ACTUAL MOVE {metrics.actual_motion_ratio * 100:4.1f}%",
        f"USEFUL      {metrics.useful_activity_ratio * 100:4.1f}%",
        f"HOLD        {metrics.holding_ratio * 100:4.1f}%",
        f"COMPLETED   {metrics.tasks_completed}",
    )
    if hasattr(engine, "production_metrics"):
        production = engine.production_metrics
        orders = tuple(engine.work_orders.values())
        lines = (
            "V5.5 MISSION EXPLAINABILITY",
            f"{orders[0].id} {orders[0].product_id} {orders[0].completed_quantity}/{orders[0].target_quantity}",
            f"{orders[1].id} {orders[1].product_id} {orders[1].completed_quantity}/{orders[1].target_quantity}",
            f"PRODUCTION {production.production_completed_units}/{production.production_target_units}",
            f"STARVATION {production.machine_starvation_time:6.1f}s",
            f"BLOCKING   {production.machine_blocking_time:6.1f}s",
            f"TRANSPORT  {production.transport_requests_completed}/{production.transport_requests_created}",
            f"WIP {production.wip_count:2d} BUFFER {production.buffer_occupancy}/{production.buffer_capacity}",
            f"ACTUAL MOVE {metrics.actual_motion_ratio * 100:4.1f}%",
        )
        counts = mission_counts(engine)
        lines += ("ACTIVE / DONE MISSIONS",) + tuple(
            f"{row.mission:<6} {row.active:2d} / {row.completed:2d}" for row in counts
        )
    for index, line in enumerate(lines):
        draw.text((995, 74 + index * 18), line, fill=(35, 35, 35))
    robot_y = 330 if is_production else 250
    for entity in engine.entities[:16]:
        task_id = engine.robot_tasks[entity.id] or "-"
        text = (_production_robot_line(engine, entity) if hasattr(engine, "production_metrics")
                else f"{entity.id} {engine.activity_states[entity.id].value:<12} {task_id}")
        if debug and engine.continuous_stationary_time[entity.id] >= 1.0:
            text += f" STILL {engine.continuous_stationary_time[entity.id]:.1f}s"
        draw.text((995, robot_y), text, fill=(45, 45, 45))
        robot_y += 13 if is_production else 16
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
        if hasattr(engine, "production_metrics"):
            debug_lines = tuple(
                f"{machine.station_id:<8} {machine.state.value:<16} {machine.current_material_id or '-'}"
                for machine in engine.machines.values()
            ) + tuple(
                f"{station:<8} BUF {buffer.occupied}/{buffer.capacity} IN+{len(buffer.inbound_reservations)}"
                for station, buffer in list(engine.buffers.items())[:4]
            ) + tuple(
                f"TRACE {event.material_unit_id} {event.event} {event.robot_id or '-'}"
                for event in engine.trace_events[-2:]
            )
        for index, line in enumerate(debug_lines):
            draw.text((995, (545 if is_production else 520) + index * 15), line, fill=(75, 40, 40))
    if is_production and selected_robot_id:
        selected = robot_mission_view(engine, selected_robot_id)
        detail = (
            f"SELECTED {selected.robot_id}",
            f"MISSION {selected.mission or '-'}",
            f"STATE {selected.operational_state}  LIFE {selected.lifecycle or '-'}",
            f"CARGO {'YES' if selected.has_cargo else 'NO'}  {selected.work_order_id or '-'}",
            f"LOT {selected.lot_id or '-'}",
            f"REQ {selected.request_id or '-'}  TASK {selected.task_id or '-'}",
            f"FROM {selected.source or '-'}",
            f"TO   {selected.destination or '-'}",
            f"PRIORITY {selected.priority or '-'}",
            f"REASON {selected.reason or '-'}",
        )
        for index, line in enumerate(detail):
            draw.text((995, 575 + index * 13), line, fill=(22, 70, 125))
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    return output


def render_warehouse_with_pillow(layout, engine, output: Path, size=(1280,720), debug=False,
                                 selected_robot_id: str | None = None):
    """Render every visible box from actual receiving/storage/staging contents."""
    from PIL import Image, ImageDraw
    image=Image.new("RGB",size,(30,30,30)); draw=ImageDraw.Draw(image)
    sx,sy=size[0]/layout.design_width,size[1]/layout.design_height
    _draw_pillow_commands(draw,build_render_plan(layout,reference_render_segments(layout,engine.graph),False),sx,sy)
    locations={**engine.receiving,**engine.storage,**engine.staging}
    sku_colors={"SKU-A":(72,145,220),"SKU-B":(50,165,105),"SKU-C":(210,135,42)}
    zones=(("RECEIVING",250,190,355,555,(225,242,252)),("STORAGE / RACK",380,190,770,555,(239,246,233)),
           ("OUTBOUND / SHIPPING",795,190,930,555,(252,239,230)))
    for label,left,top,right,bottom,color in zones:
        draw.rounded_rectangle((left,top,right,bottom),8,fill=color,outline=(110,125,130),width=2)
        draw.text((left+8,top+7),label,fill=(35,55,65))
    for location in locations.values():
        x,y=WAREHOUSE_LOCATION_ANCHORS[location.id]
        draw.rounded_rectangle((x-38,y-18,x+62,y+50),5,fill=(255,255,255),outline=(90,100,105),width=1)
        draw.text((x-34,y-15),f"{location.id} {location.occupied}/{location.capacity}",fill=(35,35,35))
    indices={}
    for box in warehouse_box_views(engine):
        x,y=WAREHOUSE_LOCATION_ANCHORS[box.location]
        index=indices.get(box.location,0); indices[box.location]=index+1
        x=x+(index%4)*20-34; y=y+(index//4)*17+7
        draw.rectangle((x*sx,y*sy,(x+13)*sx,(y+10)*sy),fill=sku_colors[box.sku],outline=(35,35,35))
        draw.text((x*sx+1,y*sy),box.label,fill=(255,255,255))
    _draw_pillow_commands(draw,motion_render_plan(engine),sx,sy)
    _draw_pillow_commands(draw,factory_status_render_plan(engine),sx,sy)
    for entity in engine.entities:
        view=warehouse_robot_view(engine,entity.id)
        if view.mission:
            x,y=entity.position(engine.graph); color=(28,130,82) if view.mission=="PUT" else (142,76,180)
            draw.rounded_rectangle((x*sx+5,y*sy-18,x*sx+88,y*sy-1),3,fill=(255,255,255),outline=color,width=2)
            cargo=f" {view.item_id[-3:]}" if view.has_cargo else ""
            draw.text((x*sx+7,y*sy-16),f"{entity.id} {view.mission[:4]} {view.phase}{cargo}",fill=color)
    m=engine.warehouse_metrics; f=engine.factory_metrics
    bysku={sku:sum(i.sku==sku and i.state.value not in {"EXPECTED","SHIPPED"} for i in engine.items.values()) for sku in ("SKU-A","SKU-B","SKU-C")}
    lines=("V5.6.1 MATERIAL FLOW",f"INBOUND {m.inbound_items_arrived} PUTAWAY {m.putaway_completed}",
           f"INVENTORY {m.inventory_total}/{m.inventory_capacity} ({m.inventory_occupancy_ratio*100:.0f}%)",
           f"ONSITE A {bysku['SKU-A']}  B {bysku['SKU-B']}  C {bysku['SKU-C']}",
           f"OUT ORDERS {m.outbound_orders_created} SHIPPED {m.outbound_orders_shipped}",
           f"ITEMS SHIPPED {m.outbound_items_shipped} STAGE {m.outbound_staging_count}",
           f"BACKORDER {m.backordered_items} RECV WAIT {m.receiving_wait_count}",
           f"MOVE {f.actual_motion_ratio*100:.1f}% IDLE {f.true_idle_ratio*100:.1f}%")
    for i,line in enumerate(lines):draw.text((995,72+i*17),line,fill=(35,35,35))
    y=225
    for entity in engine.entities:
        v=warehouse_robot_view(engine,entity.id)
        line=f"{v.robot_id} AVAILABLE"
        if v.mission: line=f"{v.robot_id} {v.mission:<7} | {v.phase:<12} {v.item_id[-3:]} {v.source}>{v.destination}"
        draw.text((995,y),line,fill=(45,45,45));y+=14
    if debug:
        debug_lines=tuple(f"{l.id:<11} {l.occupied}/{l.capacity} +{len(l.reservations)}" for l in (*engine.receiving.values(),*engine.storage.values(),*engine.staging.values()))
        debug_lines+=tuple(f"{e.time:5.1f} {e.event} {e.item_id or e.order_id or '-'}" for e in engine.events[-6:])
        for i,line in enumerate(debug_lines[-12:]):draw.text((995,465+i*18),line,fill=(80,45,45))
    if selected_robot_id:
        selected=warehouse_robot_view(engine,selected_robot_id)
        if selected.mission:
            for a,b in zip(selected.route_node_ids,selected.route_node_ids[1:]):
                first,second=engine.graph.node(a),engine.graph.node(b)
                draw.line((first.x,first.y,second.x,second.y),fill=(20,105,215),width=4)
        detail=(f"ROBOT {selected.robot_id}",f"WORK {selected.mission or 'AVAILABLE'}",f"PHASE {selected.phase}",
                f"ITEM {selected.item_id or '-'}",f"SKU {selected.sku or '-'} LOT {selected.lot_id or '-'}",
                f"FROM {selected.source or '-'}",f"TO {selected.destination or '-'}",f"ORDER {selected.order_id or '-'}",
                f"CARGO {'YES' if selected.has_cargo else 'NO'}")
        for i,line in enumerate(detail): draw.text((995,565+i*14),line,fill=(22,70,125))
    output.parent.mkdir(parents=True,exist_ok=True);image.save(output);return output


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
            ("Warehouse Multi-Robot Inventory Digital Twin - V5.6.1" if engine is not None and hasattr(engine,"warehouse_metrics")
             else "Warehouse Multi-Robot Factory - V5.5" if engine is not None and hasattr(engine, "production_metrics")
             else "Warehouse Multi-Robot Factory - V5.3") if engine is not None and hasattr(engine, "factory_metrics")
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
        self.selected_robot_id: str | None = None

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
        if self.engine is not None and hasattr(self.engine, "production_metrics") and self.selected_robot_id:
            selected = robot_mission_view(self.engine, self.selected_robot_id)
            for source_id, target_id in zip(selected.route_node_ids, selected.route_node_ids[1:]):
                source, target = self.graph.node(source_id), self.graph.node(target_id)
                commands.append(DrawCommand(Primitive.LINE, (source.x, source.y, target.x, target.y),
                                            (20, 105, 215), 4.0))
        if self.engine is not None and hasattr(self.engine,"warehouse_metrics") and self.selected_robot_id:
            selected=warehouse_robot_view(self.engine,self.selected_robot_id)
            for source_id,target_id in zip(selected.route_node_ids,selected.route_node_ids[1:]):
                source,target=self.graph.node(source_id),self.graph.node(target_id)
                commands.append(DrawCommand(Primitive.LINE,(source.x,source.y,target.x,target.y),(20,105,215),4.0))
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
        if self.engine is not None and hasattr(self.engine, "production_metrics"):
            badge_font = pygame.font.SysFont("consolas", max(8, round(9 * scale)), bold=True)
            for entity in self.engine.entities:
                view = robot_mission_view(self.engine, entity.id)
                if not view.mission:
                    continue
                x, y = entity.position(self.graph)
                label = badge_font.render(f"{entity.id} {view.mission[:3]}", True, MISSION_COLORS[view.mission], (255, 255, 255))
                self.screen.blit(label, (round(ox + (x + 6) * scale), round(oy + (y - 15) * scale)))
            if self.selected_robot_id:
                selected = robot_mission_view(self.engine, self.selected_robot_id)
                for node_id, text, color in ((selected.source_node_id, "S", (28, 135, 72)),
                                             (selected.destination_node_id, "D", (190, 55, 55))):
                    if node_id:
                        node = self.graph.node(node_id)
                        center = (round(ox + node.x * scale), round(oy + node.y * scale))
                        pygame.draw.circle(self.screen, color, center, max(6, round(8 * scale)), 2)
                        self.screen.blit(badge_font.render(text, True, color), (center[0] - 3, center[1] - 7))
        if self.engine is not None and hasattr(self.engine,"warehouse_metrics"):
            badge_font=pygame.font.SysFont("consolas",max(8,round(9*scale)),bold=True)
            sku_colors={"SKU-A":(72,145,220),"SKU-B":(50,165,105),"SKU-C":(210,135,42)}
            locations={**self.engine.receiving,**self.engine.storage,**self.engine.staging}
            zones=(("RECEIVING",250,190,355,555,(225,242,252)),("STORAGE / RACK",380,190,770,555,(239,246,233)),("OUTBOUND",795,190,930,555,(252,239,230)))
            for text,left,top,right,bottom,color in zones:
                rect=pygame.Rect(round(ox+left*scale),round(oy+top*scale),round((right-left)*scale),round((bottom-top)*scale))
                overlay=pygame.Surface(rect.size,pygame.SRCALPHA);overlay.fill((*color,70));self.screen.blit(overlay,rect.topleft)
                pygame.draw.rect(self.screen,(110,125,130),rect,max(1,round(2*scale)),border_radius=max(3,round(8*scale)))
                self.screen.blit(badge_font.render(text,True,(35,55,65)),(rect.x+7,rect.y+6))
            for location in locations.values():
                x,y=WAREHOUSE_LOCATION_ANCHORS[location.id]
                rect=pygame.Rect(round(ox+(x-38)*scale),round(oy+(y-18)*scale),round(100*scale),round(68*scale))
                pygame.draw.rect(self.screen,(255,255,255),rect,border_radius=4);pygame.draw.rect(self.screen,(90,100,105),rect,1,border_radius=4)
                self.screen.blit(badge_font.render(f"{location.id} {location.occupied}/{location.capacity}",True,(35,35,35)),(rect.x+4,rect.y+3))
            indices={}
            for box in warehouse_box_views(self.engine):
                x,y=WAREHOUSE_LOCATION_ANCHORS[box.location]
                index=indices.get(box.location,0);indices[box.location]=index+1
                x=x+(index%4)*20-34;y=y+(index//4)*17+7
                rect=pygame.Rect(round(ox+x*scale),round(oy+y*scale),max(8,round(13*scale)),max(7,round(10*scale)))
                pygame.draw.rect(self.screen,sku_colors[box.sku],rect);pygame.draw.rect(self.screen,(35,35,35),rect,1)
                self.screen.blit(badge_font.render(box.label,True,(255,255,255)),rect.topleft)
            for command in (*motion_render_plan(self.engine),*factory_status_render_plan(self.engine)):
                if command.primitive==Primitive.RECT:
                    rect=pygame.Rect(_scaled_rect(command.points,scale,scale,ox,oy));pygame.draw.rect(self.screen,command.fill,rect)
                elif command.primitive==Primitive.CIRCLE:
                    pygame.draw.ellipse(self.screen,command.fill,pygame.Rect(_scaled_rect(command.points,scale,scale,ox,oy)))
                elif command.primitive==Primitive.DIAMOND:
                    x,y,w,h=_scaled_rect(command.points,scale,scale,ox,oy);pygame.draw.polygon(self.screen,command.fill,((x+w//2,y),(x+w,y+h//2),(x+w//2,y+h),(x,y+h//2)))
            if self.selected_robot_id:
                selected=warehouse_robot_view(self.engine,self.selected_robot_id)
                for a,b in zip(selected.route_node_ids,selected.route_node_ids[1:]):
                    first,second=self.graph.node(a),self.graph.node(b)
                    pygame.draw.line(self.screen,(20,105,215),(round(ox+first.x*scale),round(oy+first.y*scale)),(round(ox+second.x*scale),round(oy+second.y*scale)),max(2,round(4*scale)))
            for entity in self.engine.entities:
                view=warehouse_robot_view(self.engine,entity.id)
                if not view.mission: continue
                x,y=entity.position(self.graph); color=(28,130,82) if view.mission=="PUT" else (142,76,180)
                cargo=f" {view.item_id[-3:]}" if view.has_cargo else ""
                self.screen.blit(badge_font.render(f"{entity.id} {view.mission[:4]} {view.phase}{cargo}",True,color,(255,255,255)),(round(ox+(x+6)*scale),round(oy+(y-15)*scale)))
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
            activity_counts = {
                activity: sum(value == activity for value in self.engine.activity_states.values())
                for activity in PhysicalActivity
            }
            panel_lines = (
                "V5.3 ACTUAL FACTORY FLOW",
                f"MOVE {activity_counts[PhysicalActivity.ACTUALLY_MOVING]:2d}  SERVICE {activity_counts[PhysicalActivity.SERVICING]:2d}",
                f"TRAFFIC WAIT {activity_counts[PhysicalActivity.TRAFFIC_WAIT]:2d}",
                f"RESOURCE WAIT {activity_counts[PhysicalActivity.RESOURCE_WAIT]:2d}",
                f"HOLD {activity_counts[PhysicalActivity.HOLDING]:2d}  IDLE {activity_counts[PhysicalActivity.TRUE_IDLE]:2d}",
                f"ACTUAL MOVE {metrics.actual_motion_ratio * 100:4.1f}%",
                f"USEFUL      {metrics.useful_activity_ratio * 100:4.1f}%",
                f"HOLD        {metrics.holding_ratio * 100:4.1f}%",
                f"COMPLETED   {metrics.tasks_completed}",
            )
            if hasattr(self.engine, "production_metrics"):
                production = self.engine.production_metrics
                orders = tuple(self.engine.work_orders.values())
                panel_lines = (
                    "V5.5 MISSION EXPLAINABILITY",
                    f"{orders[0].id} {orders[0].product_id} {orders[0].completed_quantity}/{orders[0].target_quantity}",
                    f"{orders[1].id} {orders[1].product_id} {orders[1].completed_quantity}/{orders[1].target_quantity}",
                    f"PRODUCTION {production.production_completed_units}/{production.production_target_units}",
                    f"STARVATION {production.machine_starvation_time:6.1f}s",
                    f"BLOCKING   {production.machine_blocking_time:6.1f}s",
                    f"TRANSPORT  {production.transport_requests_completed}/{production.transport_requests_created}",
                    f"WIP {production.wip_count:2d} BUFFER {production.buffer_occupancy}/{production.buffer_capacity}",
                    f"ACTUAL MOVE {metrics.actual_motion_ratio * 100:4.1f}%",
                )
                panel_lines += ("ACTIVE / DONE",) + tuple(
                    f"{row.mission:<6} {row.active:2d}/{row.completed:2d}"
                    for row in mission_counts(self.engine)
                )
            elif hasattr(self.engine,"warehouse_metrics"):
                warehouse=self.engine.warehouse_metrics
                panel_lines=("V5.6.1 MATERIAL FLOW",f"INBOUND {warehouse.inbound_items_arrived} PUT {warehouse.putaway_completed}",
                    f"INVENTORY {warehouse.inventory_total}/{warehouse.inventory_capacity}",
                    f"OUT ORDERS {warehouse.outbound_orders_created} SHIPPED {warehouse.outbound_orders_shipped}",
                    f"ITEM SHIPPED {warehouse.outbound_items_shipped} STAGE {warehouse.outbound_staging_count}",
                    f"BACKORDER {warehouse.backordered_items} RECV WAIT {warehouse.receiving_wait_count}")
            panel_x = round(ox + 990 * scale)
            panel_y = round(oy + 72 * scale)
            for index, line in enumerate(panel_lines):
                label = font.render(line, True, (35, 35, 35))
                self.screen.blit(label, (panel_x, panel_y + index * max(14, round(18 * scale))))
            robot_y = panel_y + (max(230, round(258 * scale))
                                 if hasattr(self.engine, "production_metrics")
                                 else max(160, round(180 * scale)))
            for entity in self.engine.entities[:16]:
                task_id = self.engine.robot_tasks[entity.id] or "-"
                if hasattr(self.engine,"warehouse_metrics"):
                    view=warehouse_robot_view(self.engine,entity.id)
                    line=f"{entity.id} AVAILABLE" if not view.mission else f"{entity.id} {view.mission:<7} | {view.phase:<12} {view.item_id[-3:]} {view.source}>{view.destination}"
                else:
                    line = (_production_robot_line(self.engine, entity)
                            if hasattr(self.engine, "production_metrics")
                            else f"{entity.id} {self.engine.activity_states[entity.id].value:<12} {task_id}")
                if self.show_topology_debug and self.engine.continuous_stationary_time[entity.id] >= 1.0:
                    line += f" STILL {self.engine.continuous_stationary_time[entity.id]:.1f}s"
                label = font.render(line, True, (45, 45, 45))
                self.screen.blit(label, (panel_x, robot_y))
                robot_y += (max(10, round(13 * scale))
                            if hasattr(self.engine, "production_metrics")
                            else max(12, round(16 * scale)))
            if hasattr(self.engine, "production_metrics") and self.selected_robot_id:
                selected = robot_mission_view(self.engine, self.selected_robot_id)
                selected_lines = (
                    f"SELECTED {selected.robot_id}", f"MISSION {selected.mission}",
                    f"STATE {selected.operational_state} LIFE {selected.lifecycle}",
                    f"CARGO {'YES' if selected.has_cargo else 'NO'} {selected.work_order_id}",
                    f"LOT {selected.lot_id}", f"REQ {selected.request_id} TASK {selected.task_id}",
                    f"FROM {selected.source}", f"TO {selected.destination}",
                    f"PRIORITY {selected.priority}", f"REASON {selected.reason}",
                )
                for index, line in enumerate(selected_lines):
                    self.screen.blit(font.render(line, True, (22, 70, 125)),
                                     (panel_x, round(oy + (575 + index * 13) * scale)))
            elif hasattr(self.engine,"warehouse_metrics") and self.selected_robot_id:
                selected=warehouse_robot_view(self.engine,self.selected_robot_id)
                selected_lines=(f"ROBOT {selected.robot_id}",f"WORK {selected.mission or 'AVAILABLE'}",f"PHASE {selected.phase}",
                    f"ITEM {selected.item_id or '-'}",f"SKU {selected.sku or '-'} LOT {selected.lot_id or '-'}",
                    f"FROM {selected.source or '-'}",f"TO {selected.destination or '-'}",f"ORDER {selected.order_id or '-'}",f"CARGO {'YES' if selected.has_cargo else 'NO'}")
                for index,line in enumerate(selected_lines):
                    self.screen.blit(font.render(line,True,(22,70,125)),(panel_x,round(oy+(570+index*14)*scale)))
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
                elif (event.type == self.pygame.MOUSEBUTTONDOWN and event.button == 1
                      and self.engine is not None and (hasattr(self.engine, "production_metrics") or hasattr(self.engine,"warehouse_metrics"))):
                    scale, ox, oy = self._viewport()
                    mx, my = (event.pos[0] - ox) / scale, (event.pos[1] - oy) / scale
                    nearest = min(self.engine.entities,
                                  key=lambda entity: (entity.position(self.graph)[0] - mx) ** 2
                                  + (entity.position(self.graph)[1] - my) ** 2)
                    x, y = nearest.position(self.graph)
                    self.selected_robot_id = nearest.id if (x - mx) ** 2 + (y - my) ** 2 <= 18 ** 2 else None
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
