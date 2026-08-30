"""Congestion-aware route costs and A* used only by predictive V4 traffic."""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from itertools import count
from math import hypot
from typing import Dict, Iterable, Optional

from .lane_graph import LaneGraph, LaneTraversal
from .traffic import TrafficController


@dataclass(frozen=True)
class RouteCostConfig:
    edge_reservation_penalty: float = 250.0
    node_reservation_penalty: float = 180.0
    predictive_penalty: float = 90.0
    zone_capacity_penalty: float = 120.0


@dataclass(frozen=True)
class TrafficZone:
    id: str
    node_ids: frozenset[str]
    capacity: int

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError("Zone capacity must be positive")


class CongestionModel:
    def __init__(
        self,
        graph: LaneGraph,
        controller: TrafficController,
        zones: Iterable[TrafficZone] = (),
        config: RouteCostConfig = RouteCostConfig(),
    ) -> None:
        self.graph = graph
        self.controller = controller
        self.zones = tuple(zones)
        self.config = config

    def zone_occupancy(self, zone: TrafficZone, exclude_entity: str = "") -> int:
        return sum(
            node_id in zone.node_ids and owner != exclude_entity
            for node_id, owner in self.controller.node_reservations.items()
        )

    def traversal_cost(self, traversal: LaneTraversal, entity_id: str) -> float:
        edge_owner = self.controller.owner_of_edge(traversal.edge.id)
        node_owner = self.controller.owner_of_node(traversal.target)
        cost = traversal.edge.length
        if edge_owner not in (None, entity_id):
            cost += self.config.edge_reservation_penalty
        if node_owner not in (None, entity_id):
            cost += self.config.node_reservation_penalty
        predicted = self.controller.prediction_penalty("edge", traversal.edge.id, entity_id)
        predicted += self.controller.prediction_penalty("node", traversal.target, entity_id)
        cost += self.config.predictive_penalty * predicted
        for zone in self.zones:
            if traversal.target in zone.node_ids:
                occupancy = self.zone_occupancy(zone, entity_id)
                if occupancy >= zone.capacity:
                    cost += self.config.zone_capacity_penalty * (occupancy - zone.capacity + 1)
        return cost

    def route_cost(self, route: list[str], entity_id: str) -> float:
        return sum(
            self.traversal_cost(self.graph.traversal(source, target), entity_id)
            for source, target in zip(route, route[1:])
        )


def traffic_astar(
    graph: LaneGraph,
    start: str,
    goal: str,
    model: CongestionModel,
    entity_id: str,
) -> Optional[list[str]]:
    goal_node = graph.node(goal)
    graph.node(start)
    if start == goal:
        return [start]

    def heuristic(node_id: str) -> float:
        node = graph.node(node_id)
        return hypot(goal_node.x - node.x, goal_node.y - node.y)

    serial = count()
    frontier = [(heuristic(start), 0.0, next(serial), start)]
    best = {start: 0.0}
    previous: Dict[str, str] = {}
    while frontier:
        _, cost, _, current = heapq.heappop(frontier)
        if cost != best.get(current):
            continue
        if current == goal:
            route = [current]
            while current != start:
                current = previous[current]
                route.append(current)
            route.reverse()
            return route
        for traversal in graph.traversals(current):
            new_cost = cost + model.traversal_cost(traversal, entity_id)
            if new_cost < best.get(traversal.target, float("inf")):
                best[traversal.target] = new_cost
                previous[traversal.target] = current
                heapq.heappush(frontier, (new_cost + heuristic(traversal.target), new_cost, next(serial), traversal.target))
    return None
