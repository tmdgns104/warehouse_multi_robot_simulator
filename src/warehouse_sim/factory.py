"""V5.2 factory flow with staging queues and late service reservation."""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .graph_planner import graph_astar
from .motion import LaneMobileEntity, MotionState
from .task_manager import (FactoryTaskManager, LoadState, MaterialLoad, MaterialTask,
                           RobotWorkState, TaskState, WorkStation)
from .traffic_simulation import TrafficMotionEngine


@dataclass(frozen=True)
class FactoryConfig:
    pickup_duration: float = 2.0
    drop_duration: float = 2.0
    queue_target: int = 6
    max_active_tasks: int = 10
    engagement_warmup: float = 10.0


class FactoryProfile(str, Enum):
    LIGHT = "light"
    NORMAL = "normal"
    BUSY = "busy"
    STRESS = "stress"


def factory_config_for_profile(profile: FactoryProfile | str) -> FactoryConfig:
    return {
        FactoryProfile.LIGHT: FactoryConfig(queue_target=4, max_active_tasks=6),
        FactoryProfile.NORMAL: FactoryConfig(queue_target=6, max_active_tasks=10),
        # Replenishment runs every tick, so a 12-item visible backlog can feed
        # more than 16 active assignments without inflating the queue panel.
        FactoryProfile.BUSY: FactoryConfig(queue_target=12, max_active_tasks=64),
        FactoryProfile.STRESS: FactoryConfig(queue_target=48, max_active_tasks=64),
    }[FactoryProfile(profile)]


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
    productive_ratio: float
    task_waiting_ratio: float
    engaged_ratio: float
    repositioning_utilization: float
    repositioning_ratio: float
    idle_ratio: float
    true_idle_ratio: float
    idle_robot_count: int
    true_idle_robot_count: int
    average_idle_robots: float
    average_true_idle_robots: float
    average_active_robots: float
    average_engaged_robots: float
    max_true_idle_robots_after_warmup: int
    min_engaged_robots_after_warmup: int
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
    source_wait_time: float
    destination_wait_time: float
    holding_wait_time: float
    average_source_queue_length: float
    average_destination_queue_length: float
    max_station_queue_length: int
    staging_capacity_blocks: int
    late_service_reservations: int
    station_service_utilization: float

    @property
    def assignment_blocked_station(self) -> int:
        return self.assignment_blocked_source_station + self.assignment_blocked_destination_station


class FactoryTaskGenerator:
    def __init__(self, flows: Iterable[tuple[str, ...]], *, seed: int = 1234) -> None:
        self.links = tuple((a, b) for flow in flows for a, b in zip(flow, flow[1:]))
        if not self.links:
            raise ValueError("Factory generator needs at least one material-flow link")
        self.random, self.sequence = random.Random(seed), 0

    def create(self, now: float) -> tuple[MaterialTask, MaterialLoad]:
        source, destination = self.links[self.random.randrange(len(self.links))]
        self.sequence += 1
        task_id, load_id = f"JOB-{self.sequence:04d}", f"LOAD-{self.sequence:04d}"
        task = MaterialTask(task_id, source, destination, load_id,
                            self.random.choice((1, 1, 1, 2, 3)), created_time=now)
        return task, MaterialLoad(load_id, LoadState.AT_SOURCE, source, None, task_id)


class FactoryEngine:
    """Assigns work early; staging and service capacity remain physical resources."""
    def __init__(self, traffic: TrafficMotionEngine, stations: Iterable[WorkStation],
                 flows: Iterable[tuple[str, ...]], *, seed: int = 1234,
                 config: FactoryConfig = FactoryConfig()) -> None:
        self.traffic, self.graph, self.entities = traffic, traffic.graph, traffic.entities
        self.controller = traffic.controller
        self.stations = {s.id: s for s in stations}
        self.flows, self.config, self.seed = tuple(tuple(f) for f in flows), config, seed
        for flow in self.flows:
            for station_id in flow:
                if station_id not in self.stations:
                    raise ValueError(f"Unknown flow station: {station_id}")
        self.elapsed_time, self.running = 0.0, True
        self._initialize_state()
        self._replenish_queue()

    def _initialize_state(self) -> None:
        self.generator, self.task_manager = FactoryTaskGenerator(self.flows, seed=self.seed), FactoryTaskManager()
        self.work_states = {e.id: RobotWorkState.IDLE for e in self.entities}
        self.robot_tasks: dict[str, str | None] = {e.id: None for e in self.entities}
        self.processing_remaining = {e.id: 0.0 for e in self.entities}
        self.parking_nodes = {e.id: e.current_node for e in self.entities}
        self.station_reservations: dict[str, str] = {}
        self.staging_reservations: dict[str, str] = {}
        self.task_staging: dict[str, str] = {}
        self.source_wait_queues = {sid: [] for sid in self.stations}
        self.destination_wait_queues = {sid: [] for sid in self.stations}
        self._busy_robot_time = self._productive_robot_time = self._task_waiting_robot_time = 0.0
        self._repositioning_robot_time = self._idle_robot_time = self._active_task_time = 0.0
        self._engaged_robot_time = self._true_idle_robot_time = self._engagement_measure_time = 0.0
        self._source_queue_time = self._destination_queue_time = 0.0
        self._service_task_time = 0.0
        self.source_wait_time = self.destination_wait_time = self.holding_wait_time = 0.0
        self.max_station_queue_length = self.staging_capacity_blocks = self.late_service_reservations = 0
        self._staging_blocked_tasks: set[str] = set()
        self.direct_task_handoffs = self.parking_returns = 0
        self.max_true_idle_robots_after_warmup = 0
        self.min_engaged_robots_after_warmup = len(self.entities)
        self.assignment_blocked_source_station = self.assignment_blocked_destination_station = 0
        self.assignment_blocked_max_active = self.assignment_blocked_no_idle_robot = 0
        self.assignment_blocked_no_route = 0
        self._task_block_reason: dict[str, str] = {}
        self._queued_but_dispatchable = self._queued_but_blocked = 0

    @property
    def obstacles(self):
        return self.traffic.obstacles

    def _replenish_queue(self) -> None:
        while len(self.task_manager.queued) < self.config.queue_target:
            self.task_manager.create_task(*self.generator.create(self.elapsed_time))

    def _route_length(self, start: str, goal: str) -> float | None:
        route = graph_astar(self.graph, start, goal)
        if route is None:
            return None
        return sum(self.graph.traversal(a, b).edge.length for a, b in zip(route, route[1:]))

    def _queue_key(self, task_id: str) -> tuple:
        task = self.task_manager.tasks[task_id]
        return (-task.priority, task.created_time, task.id)

    def _enqueue(self, queues: dict[str, list[str]], station_id: str, task_id: str) -> None:
        if task_id not in queues[station_id]:
            queues[station_id].append(task_id)
            queues[station_id].sort(key=self._queue_key)
        self.max_station_queue_length = max(self.max_station_queue_length, len(queues[station_id]))

    def _station_users(self, exclude_task_id: str | None = None) -> dict[str, str]:
        users = {sid: tid for sid, tid in self.station_reservations.items() if tid != exclude_task_id}
        if not self.station_reservations:  # compatibility for direct V5.1 domain tests
            for task in self.task_manager.active:
                if task.id == exclude_task_id:
                    continue
                if task.state in {TaskState.ASSIGNED, TaskState.MOVING_TO_SOURCE,
                                  TaskState.WAITING_FOR_SOURCE, TaskState.PICKING}:
                    users[task.source_station_id] = task.id
                elif task.state in {TaskState.MOVING_TO_DESTINATION,
                                    TaskState.WAITING_FOR_DESTINATION, TaskState.DROPPING}:
                    users[task.destination_station_id] = task.id
        return users

    def _record_block(self, task: MaterialTask, reason: str) -> None:
        if self._task_block_reason.get(task.id) != reason:
            self._task_block_reason[task.id] = reason
            name = f"assignment_blocked_{reason}"
            setattr(self, name, getattr(self, name) + 1)

    def _clear_block(self, task: MaterialTask) -> None:
        self._task_block_reason.pop(task.id, None)

    def _reserve_staging(self, task: MaterialTask, station_id: str) -> str | None:
        if task.id in self.task_staging:
            return self.task_staging[task.id]
        for node_id in self.stations[station_id].staging_node_ids:
            if node_id not in self.staging_reservations:
                self.staging_reservations[node_id] = task.id
                self.task_staging[task.id] = node_id
                self._staging_blocked_tasks.discard(task.id)
                return node_id
        if task.id not in self._staging_blocked_tasks:
            self.staging_capacity_blocks += 1
            self._staging_blocked_tasks.add(task.id)
        return None

    def _release_staging(self, task_id: str) -> None:
        node_id = self.task_staging.pop(task_id, None)
        if node_id and self.staging_reservations.get(node_id) == task_id:
            del self.staging_reservations[node_id]

    def _reserve_service(self, station_id: str, task_id: str) -> bool:
        owner = self.station_reservations.get(station_id)
        if owner not in (None, task_id):
            return False
        if owner is None:
            self.station_reservations[station_id] = task_id
            self.late_service_reservations += 1
        return True

    def _release_service(self, station_id: str, task_id: str) -> None:
        if self.station_reservations.get(station_id) == task_id:
            del self.station_reservations[station_id]

    def _assign(self, task: MaterialTask, entity: LaneMobileEntity, *, direct: bool = False) -> None:
        self.task_manager.assign(task, entity.id, self.elapsed_time)
        self.task_manager.reserve_load(task)
        self.task_manager.transition(task, TaskState.MOVING_TO_SOURCE, self.elapsed_time)
        self.robot_tasks[entity.id], self.work_states[entity.id] = task.id, RobotWorkState.TASK_HOLDING
        self._enqueue(self.source_wait_queues, task.source_station_id, task.id)
        self._clear_block(task)
        if direct:
            self.direct_task_handoffs += 1

    def _dispatch_entity(self, entity: LaneMobileEntity, *, direct: bool = False) -> bool:
        if len(self.task_manager.active) >= self.config.max_active_tasks:
            return False
        for task in self.task_manager.queued:
            if self._route_length(entity.current_node, self.stations[task.source_station_id].service_node_id) is not None:
                self._assign(task, entity, direct=direct)
                return True
            self._record_block(task, "no_route")
        return False

    def _assign_tasks(self) -> None:
        available = [e for e in self.entities if self.robot_tasks[e.id] is None and
                     self.work_states[e.id] in {RobotWorkState.IDLE, RobotWorkState.RETURNING}]
        for entity in sorted(available, key=lambda e: e.stable_order):
            if not self._dispatch_entity(entity):
                break
        self._queued_but_dispatchable = min(len(self.task_manager.queued),
                                            sum(self.robot_tasks[e.id] is None for e in self.entities))
        self._queued_but_blocked = len(self.task_manager.queued) - self._queued_but_dispatchable

    def _at_goal(self, entity: LaneMobileEntity, node_id: str) -> bool:
        return entity.current_edge is None and entity.current_node == node_id and entity.state == MotionState.ARRIVED

    def _entity_for_task(self, task_id: str) -> LaneMobileEntity:
        robot_id = self.task_manager.tasks[task_id].assigned_robot_id
        return next(e for e in self.entities if e.id == robot_id)

    def _clear_service_node_while_holding(self, entity: LaneMobileEntity) -> None:
        """Remote holding uses the robot's unique parking node, never a fake trip."""
        service_nodes = {station.service_node_id for station in self.stations.values()}
        parking = self.parking_nodes[entity.id]
        if entity.current_edge is None and entity.current_node in service_nodes and entity.current_node != parking:
            self.traffic.assign_goal(entity, parking)

    def _schedule_approaches(self) -> None:
        for station_id, queue in self.source_wait_queues.items():
            for task_id in tuple(queue):
                task, entity = self.task_manager.tasks[task_id], self._entity_for_task(task_id)
                if (self.work_states[entity.id] == RobotWorkState.TASK_HOLDING
                        and entity.current_edge is None and entity.state == MotionState.ARRIVED):
                    staging = self._reserve_staging(task, station_id)
                    if staging:
                        self.work_states[entity.id] = RobotWorkState.TO_SOURCE_STAGING
                        self.traffic.assign_goal(entity, staging)
                    else:
                        self._clear_service_node_while_holding(entity)
                if self.work_states[entity.id] == RobotWorkState.WAITING_SOURCE:
                    if self._reserve_service(station_id, task_id):
                        queue.remove(task_id)
                        self._release_staging(task_id)
                        self.work_states[entity.id] = RobotWorkState.TO_PICKUP
                        self.traffic.assign_goal(entity, self.stations[station_id].service_node_id)
                        break
        for station_id, queue in self.destination_wait_queues.items():
            for task_id in tuple(queue):
                task, entity = self.task_manager.tasks[task_id], self._entity_for_task(task_id)
                if (self.work_states[entity.id] == RobotWorkState.TASK_HOLDING
                        and entity.current_edge is None and entity.state == MotionState.ARRIVED):
                    staging = self._reserve_staging(task, station_id)
                    if staging:
                        self.work_states[entity.id] = RobotWorkState.TO_DESTINATION_STAGING
                        self.traffic.assign_goal(entity, staging)
                    else:
                        self._clear_service_node_while_holding(entity)
                if self.work_states[entity.id] == RobotWorkState.WAITING_DESTINATION:
                    if self._reserve_service(station_id, task_id):
                        queue.remove(task_id)
                        self._release_staging(task_id)
                        self.work_states[entity.id] = RobotWorkState.CARRYING
                        self.traffic.assign_goal(entity, self.stations[station_id].service_node_id)
                        break

    def _advance_work(self, entity: LaneMobileEntity, delta_time: float) -> None:
        task_id = self.robot_tasks[entity.id]
        if task_id is None:
            if self.work_states[entity.id] == RobotWorkState.RETURNING and self._at_goal(entity, self.parking_nodes[entity.id]):
                self.work_states[entity.id] = RobotWorkState.IDLE
            return
        task = self.task_manager.tasks[task_id]
        source, destination = (self.stations[task.source_station_id].service_node_id,
                               self.stations[task.destination_station_id].service_node_id)
        state, staging = self.work_states[entity.id], self.task_staging.get(task.id)
        if state == RobotWorkState.TO_SOURCE_STAGING and staging and self._at_goal(entity, staging):
            if task.state == TaskState.MOVING_TO_SOURCE:
                self.task_manager.transition(task, TaskState.WAITING_FOR_SOURCE, self.elapsed_time)
            self.work_states[entity.id] = RobotWorkState.WAITING_SOURCE
        elif state == RobotWorkState.TO_PICKUP and self._at_goal(entity, source):
            self.task_manager.transition(task, TaskState.PICKING, self.elapsed_time)
            self.work_states[entity.id], self.processing_remaining[entity.id] = RobotWorkState.PICKING, self.config.pickup_duration
        elif state == RobotWorkState.PICKING:
            self.processing_remaining[entity.id] -= delta_time
            if self.processing_remaining[entity.id] <= 1e-12:
                self.task_manager.pickup(task, entity.id, self.elapsed_time)
                self.task_manager.transition(task, TaskState.MOVING_TO_DESTINATION, self.elapsed_time)
                self._release_service(task.source_station_id, task.id)
                self.processing_remaining[entity.id], self.work_states[entity.id] = 0.0, RobotWorkState.TASK_HOLDING
                self._enqueue(self.destination_wait_queues, task.destination_station_id, task.id)
        elif state == RobotWorkState.TO_DESTINATION_STAGING and staging and self._at_goal(entity, staging):
            if task.state == TaskState.MOVING_TO_DESTINATION:
                self.task_manager.transition(task, TaskState.WAITING_FOR_DESTINATION, self.elapsed_time)
            self.work_states[entity.id] = RobotWorkState.WAITING_DESTINATION
        elif state == RobotWorkState.CARRYING and self._at_goal(entity, destination):
            self.task_manager.transition(task, TaskState.DROPPING, self.elapsed_time)
            self.work_states[entity.id], self.processing_remaining[entity.id] = RobotWorkState.DROPPING, self.config.drop_duration
        elif state == RobotWorkState.DROPPING:
            self.processing_remaining[entity.id] -= delta_time
            if self.processing_remaining[entity.id] <= 1e-12:
                self.task_manager.drop(task, entity.id)
                self.task_manager.transition(task, TaskState.COMPLETED, self.elapsed_time)
                self._release_service(task.destination_station_id, task.id)
                self._release_staging(task.id)
                self.robot_tasks[entity.id], self.processing_remaining[entity.id] = None, 0.0
                self._replenish_queue()
                if not self._dispatch_entity(entity, direct=True):
                    self.work_states[entity.id] = RobotWorkState.RETURNING
                    self.traffic.assign_goal(entity, self.parking_nodes[entity.id])
                    self.parking_returns += 1

    def _recover_factory_traffic_wait(self, entity: LaneMobileEntity) -> None:
        """Back off a blocked approach to remote holding before it becomes indefinite."""
        if entity.state != MotionState.WAITING or entity.waiting_time < 8.0:
            return
        task_id = self.robot_tasks[entity.id]
        if task_id is None:
            return
        task = self.task_manager.tasks[task_id]
        state = self.work_states[entity.id]
        if state in {RobotWorkState.TO_SOURCE_STAGING, RobotWorkState.TO_PICKUP}:
            self._release_staging(task.id)
            self._release_service(task.source_station_id, task.id)
            self._enqueue(self.source_wait_queues, task.source_station_id, task.id)
        elif state in {RobotWorkState.TO_DESTINATION_STAGING, RobotWorkState.CARRYING}:
            self._release_staging(task.id)
            self._release_service(task.destination_station_id, task.id)
            self._enqueue(self.destination_wait_queues, task.destination_station_id, task.id)
        else:
            return
        self.work_states[entity.id] = RobotWorkState.TASK_HOLDING
        entity.waiting_time = entity.blocked_duration = 0.0
        self.controller.clear_waiting(entity)
        self.traffic.assign_goal(entity, self.parking_nodes[entity.id])

    def _engaged(self, robot_id: str) -> bool:
        task_id = self.robot_tasks[robot_id]
        return task_id is not None and self.task_manager.tasks[task_id].state not in {
            TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED}

    def _validate_factory_reservations(self) -> None:
        if len(set(self.station_reservations.values())) != len(self.station_reservations):
            raise AssertionError("A task owns more than one station service")
        if len(set(self.staging_reservations.values())) != len(self.staging_reservations):
            raise AssertionError("A task owns more than one staging node")
        for node_id, task_id in self.staging_reservations.items():
            if self.task_staging.get(task_id) != node_id:
                raise AssertionError("Staging reservation index mismatch")
        assigned = [t.assigned_robot_id for t in self.task_manager.active if t.assigned_robot_id]
        if len(assigned) != len(set(assigned)):
            raise AssertionError("A robot owns more than one active task")
        for entity in self.entities:
            if self._engaged(entity.id) != (self.robot_tasks[entity.id] is not None):
                raise AssertionError("Engagement does not match assigned task")
        terminal = {TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED}
        reservations = set(self.station_reservations.values()) | set(self.staging_reservations.values())
        if any(self.task_manager.tasks[tid].state in terminal for tid in reservations):
            raise AssertionError("Terminal task leaked a reservation")

    def update(self, delta_time: float) -> None:
        if delta_time < 0:
            raise ValueError("delta_time cannot be negative")
        if not self.running or delta_time == 0:
            return
        self._replenish_queue(); self._assign_tasks(); self._schedule_approaches()
        self.traffic.update(delta_time); self.elapsed_time += delta_time
        for entity in self.entities:
            self._recover_factory_traffic_wait(entity)
            self._advance_work(entity, delta_time)
        self._schedule_approaches()
        productive = {RobotWorkState.TO_SOURCE_STAGING, RobotWorkState.TO_PICKUP, RobotWorkState.PICKING,
                      RobotWorkState.TO_DESTINATION_STAGING, RobotWorkState.CARRYING, RobotWorkState.DROPPING}
        waiting = {RobotWorkState.WAITING_SOURCE, RobotWorkState.WAITING_DESTINATION, RobotWorkState.TASK_HOLDING}
        states = tuple(self.work_states.values())
        self._busy_robot_time += sum(s != RobotWorkState.IDLE for s in states) * delta_time
        self._productive_robot_time += sum(s in productive for s in states) * delta_time
        self._task_waiting_robot_time += sum(s in waiting for s in states) * delta_time
        self._repositioning_robot_time += sum(s == RobotWorkState.RETURNING for s in states) * delta_time
        self._idle_robot_time += sum(s == RobotWorkState.IDLE for s in states) * delta_time
        self._active_task_time += len(self.task_manager.active) * delta_time
        self.source_wait_time += sum(s == RobotWorkState.WAITING_SOURCE for s in states) * delta_time
        self.destination_wait_time += sum(s == RobotWorkState.WAITING_DESTINATION for s in states) * delta_time
        self.holding_wait_time += sum(s == RobotWorkState.TASK_HOLDING for s in states) * delta_time
        self._source_queue_time += sum(map(len, self.source_wait_queues.values())) * delta_time
        self._destination_queue_time += sum(map(len, self.destination_wait_queues.values())) * delta_time
        self._service_task_time += len(self.station_reservations) * delta_time
        if self.elapsed_time > self.config.engagement_warmup:
            measured = min(delta_time, self.elapsed_time - self.config.engagement_warmup)
            engaged = sum(self._engaged(e.id) for e in self.entities)
            idle = len(self.entities) - engaged
            self._engaged_robot_time += engaged * measured; self._true_idle_robot_time += idle * measured
            self._engagement_measure_time += measured
            self.max_true_idle_robots_after_warmup = max(self.max_true_idle_robots_after_warmup, idle)
            self.min_engaged_robots_after_warmup = min(self.min_engaged_robots_after_warmup, engaged)
        self.task_manager.validate_load_integrity(); self._validate_factory_reservations()

    def validate_safety(self) -> None:
        self.traffic.validate_safety(); self.task_manager.validate_load_integrity(); self._validate_factory_reservations()

    def pause(self) -> None:
        self.running = False; self.traffic.pause()

    def start(self) -> None:
        self.running = True; self.traffic.start()

    def reset(self) -> None:
        self.traffic.reset(); self.controller = self.traffic.controller
        self.elapsed_time, self.running = 0.0, True; self._initialize_state(); self._replenish_queue()

    @property
    def factory_metrics(self) -> FactoryMetrics:
        completed = self.task_manager.completed
        cycle = [t.completed_time - t.created_time for t in completed]
        pickup = [t.pickup_time - t.assigned_time for t in completed]
        et = max(self.elapsed_time * len(self.entities), 1e-12)
        mt = max(self._engagement_measure_time * len(self.entities), 1e-12)
        engaged_now = sum(self._engaged(e.id) for e in self.entities)
        return FactoryMetrics(
            len(self.task_manager.tasks), len(self.task_manager.queued), len(self.task_manager.active), len(completed),
            sum(cycle)/len(cycle) if cycle else 0.0, sum(pickup)/len(pickup) if pickup else 0.0,
            self._busy_robot_time/et, self._productive_robot_time/et, self._productive_robot_time/et,
            self._task_waiting_robot_time/et, self._engaged_robot_time/mt,
            self._repositioning_robot_time/et, self._repositioning_robot_time/et,
            self._idle_robot_time/et, self._true_idle_robot_time/mt,
            sum(s == RobotWorkState.IDLE for s in self.work_states.values()), len(self.entities)-engaged_now,
            self._idle_robot_time/max(self.elapsed_time, 1e-12),
            self._true_idle_robot_time/max(self._engagement_measure_time, 1e-12),
            self._active_task_time/max(self.elapsed_time, 1e-12),
            self._engaged_robot_time/max(self._engagement_measure_time, 1e-12),
            self.max_true_idle_robots_after_warmup, self.min_engaged_robots_after_warmup,
            sum(l.state == LoadState.ON_ROBOT for l in self.task_manager.loads.values()),
            sum(t.state == TaskState.FAILED for t in self.task_manager.tasks.values()),
            self.direct_task_handoffs, self.parking_returns, self._queued_but_dispatchable, self._queued_but_blocked,
            self.assignment_blocked_source_station, self.assignment_blocked_destination_station,
            self.assignment_blocked_max_active, self.assignment_blocked_no_idle_robot, self.assignment_blocked_no_route,
            self.source_wait_time, self.destination_wait_time, self.holding_wait_time,
            self._source_queue_time/max(self.elapsed_time, 1e-12),
            self._destination_queue_time/max(self.elapsed_time, 1e-12), self.max_station_queue_length,
            self.staging_capacity_blocks, self.late_service_reservations,
            self._service_task_time/max(self.elapsed_time * len(self.stations), 1e-12))
