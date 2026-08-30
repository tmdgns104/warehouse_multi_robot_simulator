"""V5 task-driven factory material flow on the V4 traffic engine."""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from math import hypot
from typing import Iterable

from .graph_planner import graph_astar
from .motion import LaneMobileEntity, MotionState
from .task_manager import (
    FactoryTaskManager,
    LoadState,
    MaterialLoad,
    MaterialTask,
    RobotWorkState,
    TaskState,
    WorkStation,
)
from .traffic_simulation import TrafficMotionEngine


@dataclass(frozen=True)
class FactoryConfig:
    pickup_duration: float = 2.0
    drop_duration: float = 2.0
    queue_target: int = 6
    max_active_tasks: int = 10


class FactoryProfile(str, Enum):
    LIGHT = "light"
    NORMAL = "normal"
    BUSY = "busy"
    STRESS = "stress"


def factory_config_for_profile(profile: FactoryProfile | str) -> FactoryConfig:
    profile = FactoryProfile(profile)
    return {
        FactoryProfile.LIGHT: FactoryConfig(queue_target=4, max_active_tasks=6),
        FactoryProfile.NORMAL: FactoryConfig(queue_target=6, max_active_tasks=10),
        FactoryProfile.BUSY: FactoryConfig(queue_target=12, max_active_tasks=10),
        FactoryProfile.STRESS: FactoryConfig(queue_target=16, max_active_tasks=12),
    }[profile]


@dataclass(frozen=True)
class FactoryMetrics:
    tasks_created: int
    tasks_queued: int
    tasks_active: int
    tasks_completed: int
    average_task_cycle_time: float
    average_pickup_wait: float
    robot_utilization: float
    productive_utilization: float
    repositioning_utilization: float
    idle_ratio: float
    idle_robot_count: int
    average_idle_robots: float
    average_active_robots: float
    loads_in_transit: int
    failed_tasks: int
    direct_task_handoffs: int
    parking_returns: int
    queued_but_dispatchable: int
    queued_but_blocked: int
    assignment_blocked_source_station: int
    assignment_blocked_destination_station: int
    assignment_blocked_max_active: int
    assignment_blocked_no_idle_robot: int
    assignment_blocked_no_route: int

    @property
    def assignment_blocked_station(self) -> int:
        return self.assignment_blocked_source_station + self.assignment_blocked_destination_station


class FactoryTaskGenerator:
    def __init__(
        self,
        flows: Iterable[tuple[str, ...]],
        *,
        seed: int = 1234,
    ) -> None:
        self.links = tuple(
            (source, destination)
            for flow in flows
            for source, destination in zip(flow, flow[1:])
        )
        if not self.links:
            raise ValueError("Factory generator needs at least one material-flow link")
        self.random = random.Random(seed)
        self.sequence = 0

    def create(self, now: float) -> tuple[MaterialTask, MaterialLoad]:
        source, destination = self.links[self.random.randrange(len(self.links))]
        self.sequence += 1
        task_id = f"JOB-{self.sequence:04d}"
        load_id = f"LOAD-{self.sequence:04d}"
        priority = self.random.choice((1, 1, 1, 2, 3))
        return (
            MaterialTask(task_id, source, destination, load_id, priority, created_time=now),
            MaterialLoad(load_id, LoadState.AT_SOURCE, source, None, task_id),
        )


class FactoryEngine:
    """Coordinates deterministic tasks while delegating all travel to V4."""

    def __init__(
        self,
        traffic: TrafficMotionEngine,
        stations: Iterable[WorkStation],
        flows: Iterable[tuple[str, ...]],
        *,
        seed: int = 1234,
        config: FactoryConfig = FactoryConfig(),
    ) -> None:
        self.traffic = traffic
        self.graph = traffic.graph
        self.entities = traffic.entities
        self.controller = traffic.controller
        self.stations = {station.id: station for station in stations}
        self.flows = tuple(tuple(flow) for flow in flows)
        self.config = config
        self.seed = seed
        self.generator = FactoryTaskGenerator(self.flows, seed=seed)
        self.task_manager = FactoryTaskManager()
        self.work_states = {entity.id: RobotWorkState.IDLE for entity in self.entities}
        self.robot_tasks: dict[str, str | None] = {entity.id: None for entity in self.entities}
        self.processing_remaining = {entity.id: 0.0 for entity in self.entities}
        self.parking_nodes = {entity.id: entity.current_node for entity in self.entities}
        self.elapsed_time = 0.0
        self.running = True
        self._busy_robot_time = 0.0
        self._productive_robot_time = 0.0
        self._repositioning_robot_time = 0.0
        self._idle_robot_time = 0.0
        self._active_task_time = 0.0
        self.direct_task_handoffs = 0
        self.parking_returns = 0
        self.assignment_blocked_source_station = 0
        self.assignment_blocked_destination_station = 0
        self.assignment_blocked_max_active = 0
        self.assignment_blocked_no_idle_robot = 0
        self.assignment_blocked_no_route = 0
        self._task_block_reason: dict[str, str] = {}
        self._queued_but_dispatchable = 0
        self._queued_but_blocked = 0
        for flow in self.flows:
            for station_id in flow:
                if station_id not in self.stations:
                    raise ValueError(f"Unknown flow station: {station_id}")
        self._replenish_queue()

    @property
    def obstacles(self):
        return self.traffic.obstacles

    def _replenish_queue(self) -> None:
        while len(self.task_manager.queued) < self.config.queue_target:
            task, load = self.generator.create(self.elapsed_time)
            self.task_manager.create_task(task, load)

    def _route_length(self, start: str, goal: str) -> float | None:
        route = graph_astar(self.graph, start, goal)
        if route is None:
            return None
        return sum(
            self.graph.traversal(source, target).edge.length
            for source, target in zip(route, route[1:])
        )

    def _station_users(self, exclude_task_id: str | None = None) -> dict[str, str]:
        users = {}
        source_states = {TaskState.ASSIGNED, TaskState.MOVING_TO_SOURCE, TaskState.PICKING}
        destination_states = {TaskState.MOVING_TO_DESTINATION, TaskState.DROPPING}
        for task in self.task_manager.active:
            if task.id == exclude_task_id:
                continue
            if task.state in source_states:
                users[task.source_station_id] = task.id
            elif task.state in destination_states:
                users[task.destination_station_id] = task.id
        return users

    def _record_block(self, task: MaterialTask, reason: str) -> None:
        if self._task_block_reason.get(task.id) == reason:
            return
        self._task_block_reason[task.id] = reason
        attribute = f"assignment_blocked_{reason}"
        setattr(self, attribute, getattr(self, attribute) + 1)

    def _clear_block(self, task: MaterialTask) -> None:
        self._task_block_reason.pop(task.id, None)

    def _assign(self, task: MaterialTask, entity: LaneMobileEntity, *, direct: bool = False) -> None:
        source = self.stations[task.source_station_id].service_node_id
        self.task_manager.assign(task, entity.id, self.elapsed_time)
        self.task_manager.reserve_load(task)
        self.task_manager.transition(task, TaskState.MOVING_TO_SOURCE, self.elapsed_time)
        self.robot_tasks[entity.id] = task.id
        self.work_states[entity.id] = RobotWorkState.TO_PICKUP
        self.traffic.assign_goal(entity, source)
        self._clear_block(task)
        if direct:
            self.direct_task_handoffs += 1

    def _direct_handoff(self, entity: LaneMobileEntity) -> bool:
        if len(self.task_manager.active) >= self.config.max_active_tasks:
            return False
        users = self._station_users()
        for task in self.task_manager.queued:
            if task.source_station_id in users:
                continue
            source = self.stations[task.source_station_id].service_node_id
            if self._route_length(entity.current_node, source) is None:
                continue
            self._assign(task, entity, direct=True)
            return True
        return False

    def _assign_tasks(self) -> None:
        idle = [entity for entity in self.entities if self.work_states[entity.id] == RobotWorkState.IDLE]
        assignment_slots = max(0, self.config.max_active_tasks - len(self.task_manager.active))
        station_users = self._station_users()
        dispatchable = 0
        blocked = 0
        for task in self.task_manager.queued:
            if assignment_slots <= 0:
                self._record_block(task, "max_active")
                blocked += 1
                continue
            if task.source_station_id in station_users:
                self._record_block(task, "source_station")
                blocked += 1
                continue
            if not idle:
                self._record_block(task, "no_idle_robot")
                blocked += 1
                continue
            source = self.stations[task.source_station_id].service_node_id
            choices = []
            for entity in idle:
                distance = self._route_length(entity.current_node, source)
                if distance is not None:
                    choices.append((distance, entity.stable_order, entity.id, entity))
            if not choices:
                self._record_block(task, "no_route")
                blocked += 1
                continue
            dispatchable += 1
            entity = min(choices)[3]
            idle.remove(entity)
            assignment_slots -= 1
            station_users[task.source_station_id] = task.id
            self._assign(task, entity)
        # Report the remaining queue after all immediately dispatchable work
        # has been consumed by this deterministic pass.
        remaining = self.task_manager.queued
        remaining_users = self._station_users()
        remaining_idle = [
            entity for entity in self.entities
            if self.work_states[entity.id] == RobotWorkState.IDLE
        ]
        remaining_slots = max(0, self.config.max_active_tasks - len(self.task_manager.active))
        dispatchable = 0
        for task in remaining:
            if remaining_slots <= 0 or task.source_station_id in remaining_users or not remaining_idle:
                continue
            source = self.stations[task.source_station_id].service_node_id
            if any(self._route_length(entity.current_node, source) is not None for entity in remaining_idle):
                dispatchable += 1
        self._queued_but_dispatchable = dispatchable
        self._queued_but_blocked = len(remaining) - dispatchable

    def _at_goal(self, entity: LaneMobileEntity, node_id: str) -> bool:
        return entity.current_edge is None and entity.current_node == node_id and entity.state == MotionState.ARRIVED

    def _advance_work(self, entity: LaneMobileEntity, delta_time: float) -> None:
        task_id = self.robot_tasks[entity.id]
        if task_id is None and self.work_states[entity.id] == RobotWorkState.RETURNING:
            if self._at_goal(entity, self.parking_nodes[entity.id]):
                self.work_states[entity.id] = RobotWorkState.IDLE
            return
        if task_id is None:
            return
        task = self.task_manager.tasks[task_id]
        source = self.stations[task.source_station_id].service_node_id
        destination = self.stations[task.destination_station_id].service_node_id
        work_state = self.work_states[entity.id]
        if work_state == RobotWorkState.TO_PICKUP and self._at_goal(entity, source):
            self.task_manager.transition(task, TaskState.PICKING, self.elapsed_time)
            self.work_states[entity.id] = RobotWorkState.PICKING
            self.processing_remaining[entity.id] = self.config.pickup_duration
        elif work_state == RobotWorkState.PICKING:
            self.processing_remaining[entity.id] -= delta_time
            if self.processing_remaining[entity.id] <= 1e-12:
                if task.destination_station_id in self._station_users(exclude_task_id=task.id):
                    self.processing_remaining[entity.id] = 0.0
                    self._record_block(task, "destination_station")
                    return
                self._clear_block(task)
                self.task_manager.pickup(task, entity.id, self.elapsed_time)
                self.task_manager.transition(task, TaskState.MOVING_TO_DESTINATION, self.elapsed_time)
                self.work_states[entity.id] = RobotWorkState.CARRYING
                self.traffic.assign_goal(entity, destination)
        elif work_state == RobotWorkState.CARRYING and self._at_goal(entity, destination):
            self.task_manager.transition(task, TaskState.DROPPING, self.elapsed_time)
            self.work_states[entity.id] = RobotWorkState.DROPPING
            self.processing_remaining[entity.id] = self.config.drop_duration
        elif work_state == RobotWorkState.DROPPING:
            self.processing_remaining[entity.id] -= delta_time
            if self.processing_remaining[entity.id] <= 1e-12:
                self.task_manager.drop(task, entity.id)
                self.task_manager.transition(task, TaskState.COMPLETED, self.elapsed_time)
                self.robot_tasks[entity.id] = None
                self.processing_remaining[entity.id] = 0.0
                if not self._direct_handoff(entity):
                    self.work_states[entity.id] = RobotWorkState.RETURNING
                    self.traffic.assign_goal(entity, self.parking_nodes[entity.id])
                    self.parking_returns += 1

    def update(self, delta_time: float) -> None:
        if delta_time < 0:
            raise ValueError("delta_time cannot be negative")
        if not self.running or delta_time == 0:
            return
        self._replenish_queue()
        self._assign_tasks()
        self.traffic.update(delta_time)
        self.elapsed_time += delta_time
        for entity in self.entities:
            self._advance_work(entity, delta_time)
        self._busy_robot_time += sum(
            state != RobotWorkState.IDLE for state in self.work_states.values()
        ) * delta_time
        productive_states = {
            RobotWorkState.TO_PICKUP,
            RobotWorkState.PICKING,
            RobotWorkState.CARRYING,
            RobotWorkState.DROPPING,
        }
        self._productive_robot_time += sum(
            state in productive_states for state in self.work_states.values()
        ) * delta_time
        self._repositioning_robot_time += sum(
            state == RobotWorkState.RETURNING for state in self.work_states.values()
        ) * delta_time
        self._idle_robot_time += sum(
            state == RobotWorkState.IDLE for state in self.work_states.values()
        ) * delta_time
        self._active_task_time += len(self.task_manager.active) * delta_time
        self.task_manager.validate_load_integrity()

    def validate_safety(self) -> None:
        self.traffic.validate_safety()
        self.task_manager.validate_load_integrity()

    def pause(self) -> None:
        self.running = False
        self.traffic.pause()

    def start(self) -> None:
        self.running = True
        self.traffic.start()

    def reset(self) -> None:
        self.traffic.reset()
        self.controller = self.traffic.controller
        self.generator = FactoryTaskGenerator(self.flows, seed=self.seed)
        self.task_manager = FactoryTaskManager()
        self.work_states = {entity.id: RobotWorkState.IDLE for entity in self.entities}
        self.robot_tasks = {entity.id: None for entity in self.entities}
        self.processing_remaining = {entity.id: 0.0 for entity in self.entities}
        self.parking_nodes = {entity.id: entity.current_node for entity in self.entities}
        self.elapsed_time = 0.0
        self._busy_robot_time = 0.0
        self._productive_robot_time = 0.0
        self._repositioning_robot_time = 0.0
        self._idle_robot_time = 0.0
        self._active_task_time = 0.0
        self.direct_task_handoffs = 0
        self.parking_returns = 0
        self.assignment_blocked_source_station = 0
        self.assignment_blocked_destination_station = 0
        self.assignment_blocked_max_active = 0
        self.assignment_blocked_no_idle_robot = 0
        self.assignment_blocked_no_route = 0
        self._task_block_reason = {}
        self._queued_but_dispatchable = 0
        self._queued_but_blocked = 0
        self.running = True
        self._replenish_queue()

    @property
    def factory_metrics(self) -> FactoryMetrics:
        completed = self.task_manager.completed
        cycle_times = [task.completed_time - task.created_time for task in completed]
        pickup_waits = [task.pickup_time - task.assigned_time for task in completed]
        entity_time = max(self.elapsed_time * len(self.entities), 1e-12)
        return FactoryMetrics(
            tasks_created=len(self.task_manager.tasks),
            tasks_queued=len(self.task_manager.queued),
            tasks_active=len(self.task_manager.active),
            tasks_completed=len(completed),
            average_task_cycle_time=sum(cycle_times) / len(cycle_times) if cycle_times else 0.0,
            average_pickup_wait=sum(pickup_waits) / len(pickup_waits) if pickup_waits else 0.0,
            robot_utilization=self._busy_robot_time / entity_time,
            productive_utilization=self._productive_robot_time / entity_time,
            repositioning_utilization=self._repositioning_robot_time / entity_time,
            idle_ratio=self._idle_robot_time / entity_time,
            idle_robot_count=sum(state == RobotWorkState.IDLE for state in self.work_states.values()),
            average_idle_robots=self._idle_robot_time / max(self.elapsed_time, 1e-12),
            average_active_robots=self._active_task_time / max(self.elapsed_time, 1e-12),
            loads_in_transit=sum(load.state == LoadState.ON_ROBOT for load in self.task_manager.loads.values()),
            failed_tasks=sum(task.state == TaskState.FAILED for task in self.task_manager.tasks.values()),
            direct_task_handoffs=self.direct_task_handoffs,
            parking_returns=self.parking_returns,
            queued_but_dispatchable=self._queued_but_dispatchable,
            queued_but_blocked=self._queued_but_blocked,
            assignment_blocked_source_station=self.assignment_blocked_source_station,
            assignment_blocked_destination_station=self.assignment_blocked_destination_station,
            assignment_blocked_max_active=self.assignment_blocked_max_active,
            assignment_blocked_no_idle_robot=self.assignment_blocked_no_idle_robot,
            assignment_blocked_no_route=self.assignment_blocked_no_route,
        )
