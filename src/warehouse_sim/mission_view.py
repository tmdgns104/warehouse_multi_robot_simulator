"""Read-only V5.5 projections that explain production missions without changing simulation state."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .production import TransportRequestState, TransportRequestType
from .task_manager import LoadState, TaskState


MISSION_LABELS = {
    TransportRequestType.INBOUND_MOVE: "IN",
    TransportRequestType.LINE_SUPPLY: "SUPPLY",
    TransportRequestType.WIP_TRANSFER: "WIP",
    TransportRequestType.QC_TRANSFER: "QC",
    TransportRequestType.OUTBOUND_MOVE: "OUT",
}

MISSION_COLORS = {
    "IN": (92, 122, 196),
    "SUPPLY": (25, 135, 84),
    "WIP": (213, 132, 35),
    "QC": (118, 76, 175),
    "OUT": (45, 128, 184),
}


@dataclass(frozen=True)
class RobotMissionView:
    robot_id: str
    operational_state: str
    mission: str | None = None
    request_id: str | None = None
    task_id: str | None = None
    lot_id: str | None = None
    work_order_id: str | None = None
    source: str | None = None
    destination: str | None = None
    priority: str | None = None
    reason: str | None = None
    lifecycle: str | None = None
    has_cargo: bool = False
    route_node_ids: tuple[str, ...] = ()
    source_node_id: str | None = None
    destination_node_id: str | None = None


@dataclass(frozen=True)
class MissionCount:
    mission: str
    active: int
    created: int
    assigned: int
    completed: int
    average_lead_time: float


def _lifecycle(task) -> str:
    return {
        TaskState.QUEUED: "REQUESTED",
        TaskState.ASSIGNED: "ASSIGNED",
        TaskState.MOVING_TO_SOURCE: "TO SOURCE",
        TaskState.WAITING_FOR_SOURCE: "TO SOURCE",
        TaskState.PICKING: "PICK",
        TaskState.MOVING_TO_DESTINATION: "TRANSPORT",
        TaskState.WAITING_FOR_DESTINATION: "TRANSPORT",
        TaskState.DROPPING: "DROP",
        TaskState.COMPLETED: "COMPLETED",
        TaskState.FAILED: "FAILED",
        TaskState.CANCELLED: "CANCELLED",
    }[task.state]


def robot_mission_view(engine, robot_id: str) -> RobotMissionView:
    """Project one Robot's actual task/request/load/route into display-only data."""
    entity = next(entity for entity in engine.entities if entity.id == robot_id)
    task_id = engine.robot_tasks[robot_id]
    operational = engine.activity_states[robot_id].value
    if task_id is None:
        return RobotMissionView(robot_id, operational)
    task = engine.factory.task_manager.tasks[task_id]
    request = engine.requests.get(task.transport_request_id)
    if request is None:
        return RobotMissionView(robot_id, operational, task_id=task.id)
    unit = engine.materials[request.material_unit_id]
    load = engine.factory.task_manager.loads[task.load_id]
    remaining_route = tuple(entity.route[entity.route_index:])
    return RobotMissionView(
        robot_id, operational, MISSION_LABELS[request.request_type], request.id, task.id,
        unit.lot_id, request.work_order_id, request.source_location,
        request.destination_location, request.priority.name, request.reason, _lifecycle(task),
        load.state == LoadState.ON_ROBOT and load.carried_by_robot_id == robot_id,
        remaining_route,
        engine.stations[request.source_location].service_node_id,
        engine.stations[request.destination_location].service_node_id,
    )


def all_robot_missions(engine) -> tuple[RobotMissionView, ...]:
    return tuple(robot_mission_view(engine, entity.id) for entity in engine.entities)


def mission_counts(engine) -> tuple[MissionCount, ...]:
    active = Counter()
    for view in all_robot_missions(engine):
        if view.mission:
            active[view.mission] += 1
    rows = []
    for request_type in (
        TransportRequestType.LINE_SUPPLY, TransportRequestType.WIP_TRANSFER,
        TransportRequestType.QC_TRANSFER, TransportRequestType.OUTBOUND_MOVE,
    ):
        requests = [request for request in engine.requests.values()
                    if request.request_type == request_type]
        completed = [request for request in requests
                     if request.state == TransportRequestState.COMPLETED]
        assigned = [request for request in requests if request.assigned_time is not None]
        leads = [request.completed_time - request.requested_time for request in completed]
        label = MISSION_LABELS[request_type]
        rows.append(MissionCount(label, active[label], len(requests), len(assigned), len(completed),
                                 sum(leads) / len(leads) if leads else 0.0))
    return tuple(rows)
