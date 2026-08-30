"""Frame-rate-independent continuous motion along lane graph edges."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Optional

from .facility_layout import Color, EntityShape, Point
from .graph_planner import graph_astar
from .lane_graph import LaneGraph


class MotionState(str, Enum):
    IDLE = "IDLE"
    MOVING = "MOVING"
    ARRIVED = "ARRIVED"
    NO_ROUTE = "NO_ROUTE"


@dataclass
class LaneMobileEntity:
    id: str
    current_node: str
    goal_node: str
    speed: float
    color: Color = (58, 150, 26)
    shape: EntityShape = EntityShape.RECTANGLE
    width: float = 13.0
    height: float = 13.0
    route: list[str] = field(default_factory=list)
    route_index: int = 0
    current_edge: Optional[str] = None
    progress: float = 0.0
    state: MotionState = MotionState.IDLE

    def __post_init__(self) -> None:
        if self.speed <= 0:
            raise ValueError("Entity speed must be positive")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Entity size must be positive")

    def position(self, graph: LaneGraph) -> Point:
        if self.current_edge is None or self.route_index >= len(self.route) - 1:
            return graph.node(self.current_node).position
        start = graph.node(self.route[self.route_index])
        target = graph.node(self.route[self.route_index + 1])
        progress = min(1.0, max(0.0, self.progress))
        return (
            start.x + (target.x - start.x) * progress,
            start.y + (target.y - start.y) * progress,
        )


class MotionEngine:
    """Advances entities by real elapsed seconds, independent of render FPS."""

    def __init__(self, graph: LaneGraph, entities: Iterable[LaneMobileEntity]) -> None:
        self.graph = graph
        self.entities = list(entities)
        if len({entity.id for entity in self.entities}) != len(self.entities):
            raise ValueError("Motion entity IDs must be unique")
        self.elapsed_time = 0.0
        self.running = True
        self._initial = [(entity.current_node, entity.goal_node) for entity in self.entities]
        for entity in self.entities:
            self.plan(entity)

    def plan(self, entity: LaneMobileEntity) -> bool:
        route = graph_astar(self.graph, entity.current_node, entity.goal_node)
        entity.route = route or []
        entity.route_index = 0
        entity.progress = 0.0
        if route is None:
            entity.current_edge = None
            entity.state = MotionState.NO_ROUTE
            return False
        if len(route) == 1:
            entity.current_edge = None
            entity.state = MotionState.ARRIVED
            return True
        entity.current_edge = self.graph.traversal(route[0], route[1]).edge.id
        entity.state = MotionState.MOVING
        return True

    def update(self, delta_time: float) -> None:
        if delta_time < 0:
            raise ValueError("delta_time cannot be negative")
        if not self.running or delta_time == 0:
            return
        for entity in self.entities:
            self._advance(entity, entity.speed * delta_time)
        self.elapsed_time += delta_time

    def _advance(self, entity: LaneMobileEntity, distance: float) -> None:
        while distance > 1e-12 and entity.state == MotionState.MOVING:
            source_id = entity.route[entity.route_index]
            target_id = entity.route[entity.route_index + 1]
            traversal = self.graph.traversal(source_id, target_id)
            remaining = traversal.edge.length * (1.0 - entity.progress)
            if distance < remaining - 1e-12:
                entity.progress += distance / traversal.edge.length
                distance = 0.0
                continue

            distance -= remaining
            entity.current_node = target_id
            entity.route_index += 1
            entity.progress = 0.0
            if entity.route_index >= len(entity.route) - 1:
                entity.current_edge = None
                entity.state = MotionState.ARRIVED
            else:
                next_target = entity.route[entity.route_index + 1]
                entity.current_edge = self.graph.traversal(entity.current_node, next_target).edge.id

    def pause(self) -> None:
        self.running = False

    def start(self) -> None:
        self.running = True

    def reset(self) -> None:
        self.elapsed_time = 0.0
        self.running = True
        for entity, (start, goal) in zip(self.entities, self._initial):
            entity.current_node = start
            entity.goal_node = goal
            self.plan(entity)

    @property
    def all_arrived(self) -> bool:
        return bool(self.entities) and all(entity.state == MotionState.ARRIVED for entity in self.entities)

    def snapshot(self) -> tuple[tuple[str, Point, MotionState], ...]:
        return tuple((entity.id, entity.position(self.graph), entity.state) for entity in self.entities)
