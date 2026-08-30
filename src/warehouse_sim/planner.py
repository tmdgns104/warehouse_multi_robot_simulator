"""A* path planning on a four-directional warehouse grid."""

from __future__ import annotations

import heapq
from itertools import count
from typing import Dict, List, Optional

from .map import Position, WarehouseMap


def manhattan(a: Position, b: Position) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def astar(
    warehouse: WarehouseMap, start: Position, goal: Position
) -> Optional[List[Position]]:
    """Return an inclusive start-to-goal path, or ``None`` when unreachable."""
    if not warehouse.is_walkable(start) or not warehouse.is_walkable(goal):
        return None
    if start == goal:
        return [start]

    serial = count()
    frontier = [(manhattan(start, goal), 0, next(serial), start)]
    came_from: Dict[Position, Position] = {}
    best_cost = {start: 0}

    while frontier:
        _, cost, _, current = heapq.heappop(frontier)
        if cost != best_cost.get(current):
            continue
        if current == goal:
            path = [current]
            while current != start:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path

        for neighbor in warehouse.neighbors(current):
            new_cost = cost + 1
            if new_cost < best_cost.get(neighbor, 10**9):
                best_cost[neighbor] = new_cost
                came_from[neighbor] = current
                priority = new_cost + manhattan(neighbor, goal)
                heapq.heappush(
                    frontier, (priority, new_cost, next(serial), neighbor)
                )
    return None
