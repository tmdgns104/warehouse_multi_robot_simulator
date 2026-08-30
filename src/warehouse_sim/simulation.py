"""Tick-based simulation engine, independent of pygame."""

from __future__ import annotations

from typing import Callable, Iterable, List, Optional

from .collision import resolve_moves
from .map import Position, WarehouseMap, create_default_warehouse
from .planner import astar
from .robot import Robot, RobotState
from .task_manager import TaskManager

EventListener = Callable[[str], None]


class Simulation:
    def __init__(self, warehouse: WarehouseMap, robots: Iterable[Robot]) -> None:
        self.warehouse = warehouse
        self.robots = list(robots)
        if len({robot.id for robot in self.robots}) != len(self.robots):
            raise ValueError("Robot IDs must be unique")
        if len({robot.position for robot in self.robots}) != len(self.robots):
            raise ValueError("Robots cannot share a start position")
        if any(not warehouse.is_walkable(robot.position) for robot in self.robots):
            raise ValueError("Every robot must start on a walkable cell")
        self.tick_count = 0
        self.running = False
        self.events: List[str] = []
        self._initial = [(robot.id, robot.position, robot.goal) for robot in self.robots]
        self.task_manager = TaskManager(warehouse)

    def log(self, message: str) -> None:
        self.events.append(message)
        self.events = self.events[-60:]
        print(message)

    def robot(self, robot_id: int) -> Robot:
        return next(robot for robot in self.robots if robot.id == robot_id)

    def assign_goal(self, robot_id: int, goal: Position) -> bool:
        robot = self.robot(robot_id)
        try:
            self.task_manager.assign(robot, goal, self.robots)
        except ValueError as error:
            self.log(str(error))
            return False
        return self.plan_robot(robot)

    def plan_robot(self, robot: Robot) -> bool:
        if robot.goal is None:
            robot.state = RobotState.IDLE
            return False
        robot.state = RobotState.PLANNING
        path = astar(self.warehouse, robot.position, robot.goal)
        if path is None:
            robot.path.clear()
            robot.state = RobotState.IDLE
            self.log(f"Robot {robot.id}: no path to {robot.goal}")
            return False
        robot.path = path[1:]
        if robot.position == robot.goal:
            robot.state = RobotState.ARRIVED
            self.log(f"Robot {robot.id} arrived at {robot.goal}")
        else:
            robot.state = RobotState.MOVING
            self.log(f"Robot {robot.id} path planned ({len(robot.path)} steps)")
        return True

    def plan_all(self) -> None:
        for robot in self.robots:
            if robot.goal is not None:
                self.plan_robot(robot)

    def tick(self) -> None:
        """Plan if needed, resolve all intentions, then commit simultaneously."""
        for robot in self.robots:
            if robot.state == RobotState.PLANNING:
                self.plan_robot(robot)

        proposals = {robot.id: robot.next_position for robot in self.robots}
        allowed = resolve_moves(self.robots, proposals)

        for robot in self.robots:
            wants_move = proposals[robot.id] != robot.position
            if wants_move and robot.id in allowed:
                robot.position = proposals[robot.id]
                robot.path.pop(0)
                robot.waiting_count = 0
                if robot.position == robot.goal:
                    robot.state = RobotState.ARRIVED
                    self.log(f"Robot {robot.id} arrived at {robot.goal}")
                else:
                    robot.state = RobotState.MOVING
            elif wants_move:
                robot.state = RobotState.WAITING
                robot.waiting_count += 1
                self.log(f"Robot {robot.id} waiting; collision avoided")
            elif robot.goal is None:
                robot.state = RobotState.IDLE
            elif robot.position == robot.goal:
                robot.state = RobotState.ARRIVED
        self.tick_count += 1

    def start(self) -> None:
        self.running = True
        self.log("Simulation started")

    def pause(self) -> None:
        self.running = False
        self.log("Simulation paused")

    def reset(self) -> None:
        self.running = False
        self.tick_count = 0
        self.events.clear()
        for robot, (robot_id, position, goal) in zip(self.robots, self._initial):
            robot.id = robot_id
            robot.position = position
            robot.goal = goal
            robot.path.clear()
            robot.waiting_count = 0
            robot.state = RobotState.IDLE
        self.plan_all()
        self.log("Simulation reset")

    @property
    def all_arrived(self) -> bool:
        active = [robot for robot in self.robots if robot.goal is not None]
        return bool(active) and all(robot.state == RobotState.ARRIVED for robot in active)


def create_default_simulation() -> Simulation:
    warehouse = create_default_warehouse()
    robots = [
        # Independent initial routes make the first run easy to follow. Users
        # can create intersecting routes by selecting a robot and a new goal.
        Robot(1, (2, 2), (7, 2)),
        Robot(2, (19, 2), (19, 12)),
        Robot(3, (2, 13), (7, 13)),
        Robot(4, (19, 13), (18, 3)),
    ]
    simulation = Simulation(warehouse, robots)
    simulation.plan_all()
    return simulation
