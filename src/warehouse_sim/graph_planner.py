"""A* route planning for LaneGraph; V1 grid A* remains in planner.py."""

from __future__ import annotations

import heapq
from itertools import count
from math import hypot
from typing import Dict, Optional

from .lane_graph import LaneGraph


def graph_astar(graph: LaneGraph, start: str, goal: str) -> Optional[list[str]]:
    """Return a node-ID route including start and goal, or None."""
    start_node = graph.node(start)
    goal_node = graph.node(goal)
    if start == goal:
        return [start]

    def heuristic(node_id: str) -> float:
        node = graph.node(node_id)
        return hypot(goal_node.x - node.x, goal_node.y - node.y)

    serial = count()
    frontier = [(heuristic(start), 0.0, next(serial), start)]
    best_cost = {start: 0.0}
    came_from: Dict[str, str] = {}
    while frontier:
        _, cost, _, current = heapq.heappop(frontier)
        if cost != best_cost.get(current):
            continue
        if current == goal:
            route = [current]
            while current != start:
                current = came_from[current]
                route.append(current)
            route.reverse()
            return route
        for traversal in graph.traversals(current):
            new_cost = cost + traversal.edge.length
            if new_cost < best_cost.get(traversal.target, float("inf")):
                best_cost[traversal.target] = new_cost
                came_from[traversal.target] = current
                heapq.heappush(frontier, (new_cost + heuristic(traversal.target), new_cost, next(serial), traversal.target))
    return None
