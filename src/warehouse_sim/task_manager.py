"""Goal assignment kept separate from path planning and visualization."""

from __future__ import annotations

from typing import Iterable

from .map import Position, WarehouseMap
from .robot import Robot


class TaskManager:
    def __init__(self, warehouse: WarehouseMap) -> None:
        self.warehouse = warehouse

    def assign(self, robot: Robot, goal: Position, robots: Iterable[Robot]) -> None:
        if not self.warehouse.is_walkable(goal):
            raise ValueError(f"Goal is not walkable: {goal}")
        if any(other.id != robot.id and other.position == goal for other in robots):
            raise ValueError(f"Goal is occupied by another robot: {goal}")
        robot.set_goal(goal)
