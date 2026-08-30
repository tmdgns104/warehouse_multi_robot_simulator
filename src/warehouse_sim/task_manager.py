"""Goal assignment kept separate from path planning and visualization."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
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


class TaskState(str, Enum):
    QUEUED = "QUEUED"
    ASSIGNED = "ASSIGNED"
    MOVING_TO_SOURCE = "MOVING_TO_SOURCE"
    WAITING_FOR_SOURCE = "WAITING_FOR_SOURCE"
    PICKING = "PICKING"
    MOVING_TO_DESTINATION = "MOVING_TO_DESTINATION"
    WAITING_FOR_DESTINATION = "WAITING_FOR_DESTINATION"
    DROPPING = "DROPPING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class LoadState(str, Enum):
    AT_SOURCE = "AT_SOURCE"
    RESERVED = "RESERVED"
    ON_ROBOT = "ON_ROBOT"
    AT_DESTINATION = "AT_DESTINATION"


class RobotWorkState(str, Enum):
    IDLE = "IDLE"
    TO_PICKUP = "TO_PICKUP"
    TO_SOURCE_STAGING = "TO_SOURCE_STAGING"
    WAITING_SOURCE = "WAITING_SOURCE"
    PICKING = "PICKING"
    CARRYING = "CARRYING"
    TO_DESTINATION_STAGING = "TO_DEST_STAGING"
    WAITING_DESTINATION = "WAITING_DEST"
    DROPPING = "DROPPING"
    RETURNING = "RETURNING"
    TASK_HOLDING = "TASK_HOLDING"


@dataclass(frozen=True)
class WorkStation:
    id: str
    role: str
    facility_id: str
    service_node_id: str
    staging_node_ids: tuple[str, ...] = ()


@dataclass
class MaterialTask:
    id: str
    source_station_id: str
    destination_station_id: str
    load_id: str
    priority: int = 1
    state: TaskState = TaskState.QUEUED
    assigned_robot_id: str | None = None
    created_time: float = 0.0
    assigned_time: float | None = None
    pickup_time: float | None = None
    completed_time: float | None = None


@dataclass
class MaterialLoad:
    id: str
    state: LoadState
    current_station_id: str | None
    carried_by_robot_id: str | None
    task_id: str


@dataclass(frozen=True)
class TaskEvent:
    time: float
    task_id: str
    event: str
    robot_id: str | None = None


class FactoryTaskManager:
    """Deterministic V5 queue and strict task/load state transitions."""

    _TRANSITIONS = {
        TaskState.QUEUED: {TaskState.ASSIGNED, TaskState.CANCELLED},
        TaskState.ASSIGNED: {TaskState.MOVING_TO_SOURCE, TaskState.FAILED},
        TaskState.MOVING_TO_SOURCE: {
            TaskState.WAITING_FOR_SOURCE, TaskState.PICKING, TaskState.FAILED
        },
        TaskState.WAITING_FOR_SOURCE: {TaskState.PICKING, TaskState.FAILED},
        TaskState.PICKING: {TaskState.MOVING_TO_DESTINATION, TaskState.FAILED},
        TaskState.MOVING_TO_DESTINATION: {
            TaskState.WAITING_FOR_DESTINATION, TaskState.DROPPING, TaskState.FAILED
        },
        TaskState.WAITING_FOR_DESTINATION: {TaskState.DROPPING, TaskState.FAILED},
        TaskState.DROPPING: {TaskState.COMPLETED, TaskState.FAILED},
        TaskState.COMPLETED: set(),
        TaskState.FAILED: set(),
        TaskState.CANCELLED: set(),
    }

    def __init__(self) -> None:
        self.tasks: dict[str, MaterialTask] = {}
        self.loads: dict[str, MaterialLoad] = {}
        self.events: list[TaskEvent] = []

    def create_task(self, task: MaterialTask, load: MaterialLoad) -> None:
        if task.id in self.tasks or load.id in self.loads:
            raise ValueError("Task and load IDs must be unique")
        if load.task_id != task.id or load.id != task.load_id:
            raise ValueError("Task and load relationship is inconsistent")
        if load.state != LoadState.AT_SOURCE or load.current_station_id != task.source_station_id:
            raise ValueError("New load must be at the task source")
        self.tasks[task.id] = task
        self.loads[load.id] = load
        self.events.append(TaskEvent(task.created_time, task.id, TaskState.QUEUED.value))

    @property
    def queued(self) -> tuple[MaterialTask, ...]:
        return tuple(sorted(
            (task for task in self.tasks.values() if task.state == TaskState.QUEUED),
            key=lambda task: (-task.priority, task.created_time, task.id),
        ))

    @property
    def active(self) -> tuple[MaterialTask, ...]:
        terminal = {TaskState.QUEUED, TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED}
        return tuple(task for task in self.tasks.values() if task.state not in terminal)

    @property
    def completed(self) -> tuple[MaterialTask, ...]:
        return tuple(task for task in self.tasks.values() if task.state == TaskState.COMPLETED)

    def transition(self, task: MaterialTask, state: TaskState, now: float) -> None:
        if state not in self._TRANSITIONS[task.state]:
            raise ValueError(f"Invalid task transition: {task.state.value} -> {state.value}")
        task.state = state
        if state == TaskState.COMPLETED:
            task.completed_time = now
        self.events.append(TaskEvent(now, task.id, state.value, task.assigned_robot_id))

    def assign(self, task: MaterialTask, robot_id: str, now: float) -> None:
        if task.state != TaskState.QUEUED:
            raise ValueError("Only queued tasks can be assigned")
        task.assigned_robot_id = robot_id
        task.assigned_time = now
        self.transition(task, TaskState.ASSIGNED, now)

    def reserve_load(self, task: MaterialTask) -> None:
        load = self.loads[task.load_id]
        if load.state != LoadState.AT_SOURCE or load.carried_by_robot_id is not None:
            raise ValueError("Load is not available at source")
        load.state = LoadState.RESERVED

    def pickup(self, task: MaterialTask, robot_id: str, now: float) -> None:
        load = self.loads[task.load_id]
        if task.state != TaskState.PICKING or task.assigned_robot_id != robot_id:
            raise ValueError("Pickup requires assigned robot in PICKING state")
        if load.state != LoadState.RESERVED or load.carried_by_robot_id is not None:
            raise ValueError("Load cannot be picked up")
        if any(item.carried_by_robot_id == robot_id for item in self.loads.values()):
            raise ValueError("Robot already owns another load")
        load.state = LoadState.ON_ROBOT
        load.current_station_id = None
        load.carried_by_robot_id = robot_id
        task.pickup_time = now

    def drop(self, task: MaterialTask, robot_id: str) -> None:
        load = self.loads[task.load_id]
        if task.state != TaskState.DROPPING or load.carried_by_robot_id != robot_id:
            raise ValueError("Drop requires the owning robot in DROPPING state")
        load.state = LoadState.AT_DESTINATION
        load.current_station_id = task.destination_station_id
        load.carried_by_robot_id = None

    def validate_load_integrity(self) -> None:
        owners = [load.carried_by_robot_id for load in self.loads.values() if load.carried_by_robot_id]
        if len(owners) != len(set(owners)):
            raise AssertionError("A robot owns more than one load")
        for task in self.tasks.values():
            load = self.loads[task.load_id]
            if load.task_id != task.id:
                raise AssertionError("Load lost its task relationship")
            if load.state == LoadState.ON_ROBOT and load.carried_by_robot_id is None:
                raise AssertionError("Load on robot has no owner")
