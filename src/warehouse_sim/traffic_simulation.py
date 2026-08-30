"""Continuous V4 traffic simulation built on Motion + TrafficController."""

from __future__ import annotations

import random
from dataclasses import dataclass
from math import hypot
from typing import Iterable, Optional

from .graph_planner import graph_astar
from .lane_graph import LaneGraph, LaneNode
from .motion import LaneMobileEntity, MotionState
from .traffic import TrafficController


@dataclass(frozen=True)
class TrafficMetrics:
    moving_count: int
    waiting_count: int
    arrived_count: int
    total_completed_trips: int
    reservation_conflicts: int
    waiting_events: int
    deadlock_recoveries: int


class TrafficMotionEngine:
    """Plans trips, requests reservations, and advances permitted entities."""

    MAX_SUBSTEP = 0.05

    def __init__(
        self,
        graph: LaneGraph,
        entities: Iterable[LaneMobileEntity],
        *,
        seed: int = 1234,
        looping: bool = True,
        goal_candidates: Optional[Iterable[str]] = None,
        blocked_warning_seconds: float = 10.0,
    ) -> None:
        self.graph = graph
        self.entities = list(entities)
        if not self.entities:
            raise ValueError("Traffic simulation needs at least one entity")
        if len({entity.id for entity in self.entities}) != len(self.entities):
            raise ValueError("Traffic entity IDs must be unique")
        if len({entity.current_node for entity in self.entities}) != len(self.entities):
            raise ValueError("Traffic entities need unique start nodes")
        self.controller = TrafficController(blocked_warning_seconds)
        self.random = random.Random(seed)
        self.seed = seed
        self.looping = looping
        self.running = True
        self.elapsed_time = 0.0
        self.total_completed_trips = 0
        self.deadlock_recoveries = 0
        self.goal_candidates = tuple(goal_candidates or (node.id for node in graph.nodes))
        self._initial = [(entity.current_node, entity.goal_node) for entity in self.entities]
        for order, entity in enumerate(self.entities):
            graph.node(entity.current_node)
            graph.node(entity.goal_node)
            entity.stable_order = order
            self.controller.occupy_node(entity.id, entity.current_node)
            self._plan(entity)

    def _plan(self, entity: LaneMobileEntity) -> bool:
        entity.state = MotionState.PLANNING
        route = graph_astar(self.graph, entity.current_node, entity.goal_node)
        entity.route = route or []
        entity.route_index = 0
        entity.current_edge = None
        entity.progress = 0.0
        if route is None:
            entity.state = MotionState.NO_ROUTE
            return False
        if len(route) == 1:
            entity.state = MotionState.ARRIVED
            return True
        entity.state = MotionState.MOVING
        return True

    def assign_goal(self, entity: LaneMobileEntity, goal_node: str) -> bool:
        self.graph.node(goal_node)
        entity.goal_node = goal_node
        return self._plan(entity)

    def _choose_next_goal(self, entity: LaneMobileEntity) -> Optional[str]:
        current = self.graph.node(entity.current_node)
        recent = set(entity.recent_goals[-4:])
        candidates = [
            node_id
            for node_id in self.goal_candidates
            if node_id != entity.current_node and node_id not in recent
        ]
        self.random.shuffle(candidates)
        # Prefer a visually meaningful trip rather than repeated neighboring nodes.
        candidates.sort(
            key=lambda node_id: hypot(
                self.graph.node(node_id).x - current.x,
                self.graph.node(node_id).y - current.y,
            ) < 180
        )
        for candidate in candidates:
            if graph_astar(self.graph, entity.current_node, candidate) is not None:
                entity.recent_goals.append(entity.goal_node)
                entity.recent_goals = entity.recent_goals[-4:]
                return candidate
        return None

    def update(self, delta_time: float) -> None:
        if delta_time < 0:
            raise ValueError("delta_time cannot be negative")
        if not self.running or delta_time == 0:
            return
        remaining = delta_time
        while remaining > 1e-12:
            step = min(self.MAX_SUBSTEP, remaining)
            self._update_step(step)
            remaining -= step
        self.elapsed_time += delta_time

    def _update_step(self, delta_time: float) -> None:
        if self.looping:
            for entity in self.entities:
                if entity.state == MotionState.ARRIVED:
                    next_goal = self._choose_next_goal(entity)
                    if next_goal is None:
                        entity.state = MotionState.NO_ROUTE
                    else:
                        self.assign_goal(entity, next_goal)

        candidates = [
            entity
            for entity in self.entities
            if entity.current_edge is None
            and entity.state in (MotionState.MOVING, MotionState.WAITING)
            and entity.route_index < len(entity.route) - 1
        ]
        for entity in sorted(candidates, key=self.controller.priority_key):
            source = entity.route[entity.route_index]
            target = entity.route[entity.route_index + 1]
            traversal = self.graph.traversal(source, target)
            was_waiting = entity.state == MotionState.WAITING
            decision = self.controller.request_entry(
                entity.id, entity.current_node, traversal.edge, target
            )
            if decision.granted:
                entity.current_edge = traversal.edge.id
                entity.progress = 0.0
                entity.state = MotionState.MOVING
                entity.waiting_count = 0
                self.controller.clear_waiting(entity)
            else:
                entity.state = MotionState.WAITING
                self.controller.note_waiting(entity, delta_time, not was_waiting)

        # Limited demo recovery: after a warning threshold, choose one free
        # adjacent node as a short new goal. This keeps the visual demo alive
        # without pretending to be a general deadlock solver or MAPF rerouter.
        if self.looping:
            blocked = sorted(
                (
                    entity for entity in self.entities
                    if entity.state == MotionState.WAITING
                    and entity.waiting_time >= self.controller.blocked_warning_seconds
                ),
                key=self.controller.priority_key,
            )
            for entity in blocked:
                options = sorted(
                    self.graph.traversals(entity.current_node),
                    key=lambda traversal: traversal.target,
                )
                escape = next(
                    (
                        traversal for traversal in options
                        if self.controller.owner_of_edge(traversal.edge.id) is None
                        and self.controller.owner_of_node(traversal.target) is None
                    ),
                    None,
                )
                if escape is not None:
                    self.assign_goal(entity, escape.target)
                    entity.waiting_time = 0.0
                    self.deadlock_recoveries += 1
                    self.controller.events.append(
                        f"Traffic recovery: {entity.id} assigned adjacent goal {escape.target}"
                    )
                    break

        for entity in self.entities:
            if entity.current_edge is None or entity.state != MotionState.MOVING:
                continue
            source_id = entity.route[entity.route_index]
            target_id = entity.route[entity.route_index + 1]
            traversal = self.graph.traversal(source_id, target_id)
            next_progress = entity.progress + entity.speed * delta_time / traversal.edge.length
            if next_progress < 1.0 - 1e-12:
                entity.progress = next_progress
                continue
            completed_edge = entity.current_edge
            entity.current_node = target_id
            entity.route_index += 1
            entity.progress = 0.0
            entity.current_edge = None
            self.controller.complete_edge(entity.id, completed_edge, target_id)
            if entity.route_index >= len(entity.route) - 1:
                entity.state = MotionState.ARRIVED
                entity.completed_trips += 1
                self.total_completed_trips += 1

    def pause(self) -> None:
        self.running = False

    def start(self) -> None:
        self.running = True

    def reset(self) -> None:
        self.controller = TrafficController(self.controller.blocked_warning_seconds)
        self.random = random.Random(self.seed)
        self.elapsed_time = 0.0
        self.total_completed_trips = 0
        self.deadlock_recoveries = 0
        self.running = True
        for order, (entity, (start, goal)) in enumerate(zip(self.entities, self._initial)):
            entity.current_node = start
            entity.goal_node = goal
            entity.current_edge = None
            entity.progress = 0.0
            entity.waiting_count = 0
            entity.waiting_time = 0.0
            entity.completed_trips = 0
            entity.recent_goals.clear()
            entity.stable_order = order
            self.controller.occupy_node(entity.id, start)
            self._plan(entity)

    def position(self, entity: LaneMobileEntity):
        return entity.position(self.graph)

    def snapshot(self):
        return tuple((entity.id, entity.position(self.graph), entity.state) for entity in self.entities)

    @property
    def metrics(self) -> TrafficMetrics:
        return TrafficMetrics(
            moving_count=sum(entity.state == MotionState.MOVING for entity in self.entities),
            waiting_count=sum(entity.state == MotionState.WAITING for entity in self.entities),
            arrived_count=sum(entity.state == MotionState.ARRIVED for entity in self.entities),
            total_completed_trips=self.total_completed_trips,
            reservation_conflicts=self.controller.conflict_count,
            waiting_events=self.controller.waiting_events,
            deadlock_recoveries=self.deadlock_recoveries,
        )

    def validate_safety(self) -> None:
        """Raise if ownership or continuous positions violate V4 invariants."""
        node_entities = [entity for entity in self.entities if entity.current_edge is None]
        if len({entity.current_node for entity in node_entities}) != len(node_entities):
            raise AssertionError("Multiple entities occupy the same node")
        for entity in self.entities:
            if entity.current_edge is None:
                if self.controller.owner_of_node(entity.current_node) != entity.id:
                    raise AssertionError(f"Missing node reservation for {entity.id}")
            else:
                if self.controller.owner_of_edge(entity.current_edge) != entity.id:
                    raise AssertionError(f"Missing edge reservation for {entity.id}")
                target = entity.route[entity.route_index + 1]
                if self.controller.owner_of_node(target) != entity.id:
                    raise AssertionError(f"Missing target reservation for {entity.id}")
