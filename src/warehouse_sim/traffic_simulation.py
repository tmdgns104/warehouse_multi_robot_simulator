"""Continuous V4 traffic simulation built on Motion + TrafficController."""

from __future__ import annotations

import random
from dataclasses import dataclass
from math import hypot
from typing import Iterable, Optional

from .graph_planner import graph_astar
from .lane_graph import LaneGraph
from .motion import LaneMobileEntity, MotionState
from .traffic import TrafficController
from .traffic_planner import CongestionModel, RouteCostConfig, TrafficZone, traffic_astar


@dataclass(frozen=True)
class TrafficMetrics:
    moving_count: int
    waiting_count: int
    arrived_count: int
    total_completed_trips: int
    reservation_conflicts: int
    waiting_events: int
    deadlock_recoveries: int
    entity_count: int
    slowed_count: int
    head_on_conflict_count: int
    head_on_conflicts_prevented: int
    reroute_count: int
    stop_count: int
    deadlock_count: int
    deadlock_prevented_count: int
    indefinite_wait_count: int
    stopped_over_5s: int
    max_wait_time: float
    average_wait_time: float
    average_speed: float
    moving_ratio: float
    throughput_per_minute: float


class TrafficMotionEngine:
    """Plans trips, requests reservations, and advances permitted entities."""

    MAX_SUBSTEP = 0.05
    RESERVATION_HORIZON = 4
    REROUTE_COOLDOWN = 3.0
    REROUTE_IMPROVEMENT = 0.90
    SERIOUS_BLOCK_SECONDS = 5.0
    SPEED_ACCELERATION = 24.0

    def __init__(
        self,
        graph: LaneGraph,
        entities: Iterable[LaneMobileEntity],
        *,
        seed: int = 1234,
        looping: bool = True,
        goal_candidates: Optional[Iterable[str]] = None,
        blocked_warning_seconds: float = 10.0,
        zones: Iterable[TrafficZone] = (),
        route_cost_config: RouteCostConfig = RouteCostConfig(),
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
        self.congestion = CongestionModel(graph, self.controller, zones, route_cost_config)
        self.random = random.Random(seed)
        self.seed = seed
        self.looping = looping
        self.running = True
        self.elapsed_time = 0.0
        self.total_completed_trips = 0
        self.deadlock_recoveries = 0
        self._moving_entity_time = 0.0
        self._total_entity_time = 0.0
        self._speed_integral = 0.0
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
        route = traffic_astar(
            self.graph, entity.current_node, entity.goal_node, self.congestion, entity.id
        )
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
        active_goals = [other.goal_node for other in self.entities if other.id != entity.id]
        candidates.sort(key=lambda node_id: (
            active_goals.count(node_id),
            self.controller.prediction_penalty("node", node_id, entity.id),
            hypot(self.graph.node(node_id).x - current.x, self.graph.node(node_id).y - current.y) < 180,
        ))
        for candidate in candidates:
            if traffic_astar(self.graph, entity.current_node, candidate, self.congestion, entity.id) is not None:
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
        now = self.elapsed_time
        self.controller.expire_predictions(now)
        if self.looping:
            for entity in self.entities:
                if entity.state == MotionState.ARRIVED:
                    next_goal = self._choose_next_goal(entity)
                    if next_goal is None:
                        entity.state = MotionState.NO_ROUTE
                    else:
                        self.assign_goal(entity, next_goal)

        for entity in self.entities:
            self._refresh_prediction(entity)

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
                entity.blocked_duration = 0.0
                entity.target_speed = entity.preferred_speed
                self.controller.clear_waiting(entity)
            else:
                rerouted = self._try_reroute(entity, force=decision.cycle_prevented)
                if not rerouted:
                    entity.state = MotionState.WAITING
                    entity.target_speed = 0.0
                    entity.blocked_duration += delta_time
                    entity.total_wait_time += delta_time
                    entity.max_wait_time = max(entity.max_wait_time, entity.waiting_time + delta_time)
                    if not was_waiting:
                        entity.stop_count += 1
                    self.controller.note_waiting(entity, delta_time, not was_waiting)

        # Limited demo recovery: after a warning threshold, choose one free
        # adjacent node as a short new goal. This keeps the visual demo alive
        # without pretending to be a general deadlock solver or MAPF rerouter.
        if self.looping:
            blocked = sorted(
                (
                    entity for entity in self.entities
                    if entity.state == MotionState.WAITING
                    and entity.waiting_time >= self.SERIOUS_BLOCK_SECONDS
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
                    entity.reroute_count += 1
                    entity.last_reroute_time = now
                    entity.stopped_over_threshold_count += 1
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
            self._coordinate_speed(entity, delta_time)
            next_progress = entity.progress + entity.current_speed * delta_time / traversal.edge.length
            if next_progress < 1.0 - 1e-12:
                entity.progress = next_progress
                entity.last_progress_time = now
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

        moving_now = sum(
            entity.state == MotionState.MOVING and entity.current_speed > 0.5
            for entity in self.entities
        )
        self._moving_entity_time += moving_now * delta_time
        self._total_entity_time += len(self.entities) * delta_time
        self._speed_integral += sum(entity.current_speed for entity in self.entities) * delta_time

    def _refresh_prediction(self, entity: LaneMobileEntity) -> None:
        if not entity.route or entity.route_index >= len(entity.route) - 1:
            self.controller.remove_predictions(entity.id)
            return
        resources = []
        eta = 0.0
        end = min(len(entity.route) - 1, entity.route_index + self.RESERVATION_HORIZON)
        for index in range(entity.route_index, end):
            source, target = entity.route[index], entity.route[index + 1]
            traversal = self.graph.traversal(source, target)
            eta += traversal.edge.length / max(entity.current_speed, entity.minimum_moving_speed)
            resources.append(("edge", traversal.edge.id, eta))
            resources.append(("node", target, eta))
        self.controller.refresh_predictions(entity.id, resources, ttl=0.2)

    def _try_reroute(self, entity: LaneMobileEntity, force: bool = False) -> bool:
        if not force and self.elapsed_time - entity.last_reroute_time < self.REROUTE_COOLDOWN:
            return False
        new_route = traffic_astar(
            self.graph, entity.current_node, entity.goal_node, self.congestion, entity.id
        )
        if not new_route or len(new_route) < 2:
            return False
        current_route = entity.route[entity.route_index:]
        if new_route == current_route:
            return False
        old_cost = self.congestion.route_cost(current_route, entity.id)
        new_cost = self.congestion.route_cost(new_route, entity.id)
        if not force and new_cost >= old_cost * self.REROUTE_IMPROVEMENT:
            return False
        entity.route = new_route
        entity.route_index = 0
        entity.current_edge = None
        entity.progress = 0.0
        entity.state = MotionState.MOVING
        entity.reroute_count += 1
        entity.last_reroute_time = self.elapsed_time
        return True

    def _coordinate_speed(self, entity: LaneMobileEntity, delta_time: float) -> None:
        prediction = 0.0
        if entity.route_index + 2 < len(entity.route):
            next_traversal = self.graph.traversal(
                entity.route[entity.route_index + 1], entity.route[entity.route_index + 2]
            )
            prediction += self.controller.prediction_penalty("edge", next_traversal.edge.id, entity.id)
            prediction += self.controller.prediction_penalty("node", next_traversal.target, entity.id)
        entity.target_speed = (
            max(entity.minimum_moving_speed, entity.preferred_speed * 0.55)
            if prediction > 0.5
            else entity.preferred_speed
        )
        change = self.SPEED_ACCELERATION * delta_time
        if entity.current_speed < entity.target_speed:
            entity.current_speed = min(entity.target_speed, entity.current_speed + change)
        else:
            entity.current_speed = max(entity.target_speed, entity.current_speed - change)

    def pause(self) -> None:
        self.running = False

    def start(self) -> None:
        self.running = True

    def reset(self) -> None:
        self.controller = TrafficController(self.controller.blocked_warning_seconds)
        self.congestion = CongestionModel(
            self.graph, self.controller, self.congestion.zones, self.congestion.config
        )
        self.random = random.Random(self.seed)
        self.elapsed_time = 0.0
        self.total_completed_trips = 0
        self.deadlock_recoveries = 0
        self._moving_entity_time = 0.0
        self._total_entity_time = 0.0
        self._speed_integral = 0.0
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
            entity.total_wait_time = 0.0
            entity.max_wait_time = 0.0
            entity.blocked_duration = 0.0
            entity.reroute_count = 0
            entity.stop_count = 0
            entity.stopped_over_threshold_count = 0
            entity.current_speed = entity.preferred_speed
            entity.target_speed = entity.preferred_speed
            entity.stable_order = order
            self.controller.occupy_node(entity.id, start)
            self._plan(entity)

    def position(self, entity: LaneMobileEntity):
        return entity.position(self.graph)

    def snapshot(self):
        return tuple((entity.id, entity.position(self.graph), entity.state) for entity in self.entities)

    @property
    def metrics(self) -> TrafficMetrics:
        elapsed = max(self.elapsed_time, 1e-12)
        total_wait = sum(entity.total_wait_time for entity in self.entities)
        return TrafficMetrics(
            moving_count=sum(entity.state == MotionState.MOVING for entity in self.entities),
            waiting_count=sum(entity.state == MotionState.WAITING for entity in self.entities),
            arrived_count=sum(entity.state == MotionState.ARRIVED for entity in self.entities),
            total_completed_trips=self.total_completed_trips,
            reservation_conflicts=self.controller.conflict_count,
            waiting_events=self.controller.waiting_events,
            deadlock_recoveries=self.deadlock_recoveries,
            entity_count=len(self.entities),
            slowed_count=sum(
                entity.state == MotionState.MOVING
                and entity.current_speed < entity.preferred_speed * 0.9
                for entity in self.entities
            ),
            head_on_conflict_count=0,
            head_on_conflicts_prevented=self.controller.head_on_conflict_count,
            reroute_count=sum(entity.reroute_count for entity in self.entities),
            stop_count=sum(entity.stop_count for entity in self.entities),
            deadlock_count=0,
            deadlock_prevented_count=self.controller.deadlock_prevented_count,
            indefinite_wait_count=sum(entity.waiting_time >= 10.0 for entity in self.entities),
            stopped_over_5s=sum(entity.stopped_over_threshold_count for entity in self.entities),
            max_wait_time=max((entity.max_wait_time for entity in self.entities), default=0.0),
            average_wait_time=total_wait / len(self.entities),
            average_speed=self._speed_integral / (len(self.entities) * elapsed),
            moving_ratio=self._moving_entity_time / max(self._total_entity_time, 1e-12),
            throughput_per_minute=self.total_completed_trips / elapsed * 60.0,
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
        for owners in self.controller.predictive_reservations.values():
            if any(record.expires_at < self.controller.current_time for record in owners.values()):
                raise AssertionError("Stale predictive reservation")
