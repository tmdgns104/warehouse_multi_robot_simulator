"""Synthetic manufacturing demand layered over the reference-derived layout."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Iterable

from .factory import FactoryEngine
from .task_manager import LoadState, MaterialLoad, MaterialTask, TaskState


class WorkOrderState(str, Enum):
    PLANNED = "PLANNED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"


class MaterialUnitState(str, Enum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    IN_TRANSIT = "IN_TRANSIT"
    AT_PROCESS = "AT_PROCESS"
    PROCESSING = "PROCESSING"
    WAITING_TRANSFER = "WAITING_TRANSFER"
    FINISHED = "FINISHED"
    SHIPPED = "SHIPPED"


class MachineState(str, Enum):
    IDLE = "IDLE"
    WAITING_MATERIAL = "WAITING_MATERIAL"
    PROCESSING = "PROCESSING"
    WAITING_UNLOAD = "WAITING_UNLOAD"


class TransportRequestType(str, Enum):
    INBOUND_MOVE = "INBOUND_MOVE"
    LINE_SUPPLY = "LINE_SUPPLY"
    WIP_TRANSFER = "WIP_TRANSFER"
    QC_TRANSFER = "QC_TRANSFER"
    OUTBOUND_MOVE = "OUTBOUND_MOVE"


class TransportPriority(IntEnum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class TransportRequestState(str, Enum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


@dataclass
class WorkOrder:
    id: str
    product_id: str
    target_quantity: int
    priority: TransportPriority = TransportPriority.NORMAL
    created_time: float = 0.0
    due_time: float = 300.0
    completed_quantity: int = 0
    state: WorkOrderState = WorkOrderState.PLANNED

    def start(self) -> None:
        if self.state != WorkOrderState.PLANNED:
            raise ValueError("Only planned work orders can start")
        self.state = WorkOrderState.RUNNING

    def complete_unit(self) -> None:
        if self.state != WorkOrderState.RUNNING:
            raise ValueError("Work order must be running")
        if self.completed_quantity >= self.target_quantity:
            raise ValueError("Work order target already completed")
        self.completed_quantity += 1
        if self.completed_quantity == self.target_quantity:
            self.state = WorkOrderState.COMPLETED


@dataclass
class MaterialUnit:
    id: str
    material_id: str
    lot_id: str
    quantity: int
    work_order_id: str
    current_location: str | None
    state: MaterialUnitState = MaterialUnitState.AVAILABLE
    active_request_id: str | None = None


@dataclass(frozen=True)
class MaterialTraceEvent:
    time: float
    material_unit_id: str
    event: str
    from_location: str | None
    to_location: str | None
    robot_id: str | None
    transport_request_id: str | None
    material_task_id: str | None
    work_order_id: str


@dataclass
class MaterialBuffer:
    id: str
    station_id: str
    capacity: int
    contents: list[str] = field(default_factory=list)
    inbound_reservations: set[str] = field(default_factory=set)
    maximum_occupancy: int = 0

    @property
    def occupied(self) -> int:
        return len(self.contents)

    @property
    def free(self) -> int:
        return self.capacity - self.occupied - len(self.inbound_reservations)

    def add(self, material_id: str) -> None:
        if material_id in self.contents:
            raise ValueError("Material already exists in buffer")
        if self.occupied >= self.capacity:
            raise ValueError("Buffer capacity exceeded")
        self.contents.append(material_id)
        self.maximum_occupancy = max(self.maximum_occupancy, self.occupied)

    def remove(self, material_id: str) -> None:
        if material_id not in self.contents:
            raise ValueError("Material is not in buffer")
        self.contents.remove(material_id)

    def reserve_inbound(self, request_id: str) -> bool:
        if request_id in self.inbound_reservations:
            return True
        if self.free <= 0:
            return False
        self.inbound_reservations.add(request_id)
        return True

    def receive(self, request_id: str, material_id: str) -> None:
        if request_id not in self.inbound_reservations:
            raise ValueError("Inbound capacity was not reserved")
        self.inbound_reservations.remove(request_id)
        self.add(material_id)


@dataclass
class ProductionMachine:
    id: str
    station_id: str
    next_station_id: str
    processing_time: float
    request_type: TransportRequestType
    state: MachineState = MachineState.WAITING_MATERIAL
    current_material_id: str | None = None
    remaining_time: float = 0.0
    starvation_time: float = 0.0
    blocking_time: float = 0.0
    completed_cycles: int = 0


@dataclass
class TransportRequest:
    id: str
    request_type: TransportRequestType
    work_order_id: str
    material_unit_id: str
    source_location: str
    destination_location: str
    priority: TransportPriority
    reason: str
    requested_time: float
    due_time: float
    state: TransportRequestState = TransportRequestState.OPEN
    material_task_id: str | None = None
    assigned_time: float | None = None
    completed_time: float | None = None


@dataclass(frozen=True)
class ProductionMetrics:
    production_completed_units: int
    production_target_units: int
    production_throughput: float
    machine_starvation_time: float
    machine_blocking_time: float
    average_transport_lead_time: float
    on_time_transport_rate: float
    wip_count: int
    buffer_occupancy: int
    buffer_capacity: int
    inventory_accuracy_errors: int
    transport_requests_created: int
    transport_requests_completed: int
    open_transport_requests: int
    active_transport_requests: int


class ProductionEngine:
    """Turns deterministic production state into executable robot transport tasks."""

    def __init__(self, factory: FactoryEngine, *, target_per_product: int = 10) -> None:
        self.factory = factory
        self.target_per_product = target_per_product
        self.elapsed_time = 0.0
        self.running = True
        self.work_orders = {
            "WO-A": WorkOrder("WO-A", "PRODUCT-A", target_per_product, due_time=300.0),
            "WO-B": WorkOrder("WO-B", "PRODUCT-B", target_per_product, due_time=300.0),
        }
        for order in self.work_orders.values():
            order.start()
        self.buffers = {
            station: MaterialBuffer(f"BUF-{station}", station, capacity)
            for station, capacity in {
                "IN_A": target_per_product, "PROC_A": 3, "QC_A": 3, "OUT_A": target_per_product,
                "IN_B": target_per_product, "PROC_B": 3, "BUFFER_B": 3, "OUT_B": target_per_product,
            }.items()
        }
        self.machines = {
            "PROC_A": ProductionMachine("MACHINE-PROC-A", "PROC_A", "QC_A", 12.0,
                                         TransportRequestType.QC_TRANSFER),
            "QC_A": ProductionMachine("MACHINE-QC-A", "QC_A", "OUT_A", 6.0,
                                       TransportRequestType.OUTBOUND_MOVE),
            "PROC_B": ProductionMachine("MACHINE-PROC-B", "PROC_B", "BUFFER_B", 12.0,
                                         TransportRequestType.WIP_TRANSFER),
            "BUFFER_B": ProductionMachine("MACHINE-QC-B", "BUFFER_B", "OUT_B", 6.0,
                                           TransportRequestType.OUTBOUND_MOVE),
        }
        self.materials: dict[str, MaterialUnit] = {}
        self.requests: dict[str, TransportRequest] = {}
        self.trace_events: list[MaterialTraceEvent] = []
        self.request_sequence = 0
        self.task_sequence = 0
        self.inventory_accuracy_errors = 0
        self._known_completed_tasks: set[str] = set()
        for label, input_station in (("A", "IN_A"), ("B", "IN_B")):
            for index in range(1, target_per_product + 1):
                material_id = f"MAT-{label}-{index:03d}"
                unit = MaterialUnit(material_id, f"RAW-{label}", f"LOT-{label}-{index:03d}", 1,
                                    f"WO-{label}", input_station)
                self.materials[material_id] = unit
                self.buffers[input_station].add(material_id)
                self._trace(unit, "CREATED", None, input_station)
        self._issue_required_requests()

    def __getattr__(self, name):
        return getattr(self.factory, name)

    @property
    def factory_metrics(self):
        return self.factory.factory_metrics

    def _trace(self, unit: MaterialUnit, event: str, source: str | None, destination: str | None,
               *, robot_id: str | None = None, request_id: str | None = None,
               task_id: str | None = None) -> None:
        self.trace_events.append(MaterialTraceEvent(
            self.elapsed_time, unit.id, event, source, destination, robot_id,
            request_id, task_id, unit.work_order_id,
        ))

    def _has_pending_for_destination(self, destination: str) -> bool:
        return any(request.destination_location == destination and request.state != TransportRequestState.COMPLETED
                   for request in self.requests.values())

    def _create_request(self, unit: MaterialUnit, destination: str,
                        request_type: TransportRequestType, priority: TransportPriority,
                        reason: str) -> TransportRequest | None:
        if unit.active_request_id is not None or unit.current_location is None:
            return None
        self.request_sequence += 1
        request_id = f"TR-{self.request_sequence:04d}"
        destination_buffer = self.buffers[destination]
        if not destination_buffer.reserve_inbound(request_id):
            self.request_sequence -= 1
            return None
        request = TransportRequest(
            request_id, request_type, unit.work_order_id, unit.id,
            unit.current_location, destination, priority, reason,
            self.elapsed_time, self.elapsed_time + 60.0,
        )
        self.requests[request.id] = request
        unit.active_request_id = request.id
        unit.state = MaterialUnitState.RESERVED
        self.task_sequence += 1
        task_id, load_id = f"JOB-P{self.task_sequence:04d}", f"LOAD-{request.id}"
        task = MaterialTask(
            task_id, request.source_location, request.destination_location, load_id,
            int(priority), created_time=self.elapsed_time, transport_request_id=request.id,
        )
        load = MaterialLoad(load_id, LoadState.AT_SOURCE, request.source_location, None, task.id)
        self.factory.task_manager.create_task(task, load)
        request.material_task_id = task.id
        self._trace(unit, "REQUESTED", request.source_location, destination,
                    request_id=request.id, task_id=task.id)
        return request

    def _issue_required_requests(self) -> None:
        for label, input_station, machine_station in (
            ("A", "IN_A", "PROC_A"), ("B", "IN_B", "PROC_B")
        ):
            machine = self.machines[machine_station]
            if machine.current_material_id is not None or self.buffers[machine_station].contents:
                continue
            if self._has_pending_for_destination(machine_station):
                continue
            candidate = next((self.materials[mid] for mid in self.buffers[input_station].contents
                              if self.materials[mid].work_order_id == f"WO-{label}"
                              and self.materials[mid].active_request_id is None), None)
            if candidate:
                priority = TransportPriority.CRITICAL if machine.starvation_time > 0 else TransportPriority.HIGH
                self._create_request(candidate, machine_station, TransportRequestType.LINE_SUPPLY,
                                     priority, "PRODUCTION_SUPPLY")

    def _sync_requests(self) -> None:
        for request in self.requests.values():
            if request.material_task_id is None:
                continue
            task = self.factory.task_manager.tasks[request.material_task_id]
            unit = self.materials[request.material_unit_id]
            if task.state not in {TaskState.QUEUED, TaskState.COMPLETED} and request.state == TransportRequestState.OPEN:
                request.state = TransportRequestState.ASSIGNED
                request.assigned_time = task.assigned_time
                self._trace(unit, "ASSIGNED", request.source_location, request.destination_location,
                            robot_id=task.assigned_robot_id, request_id=request.id, task_id=task.id)
            if task.pickup_time is not None and request.state in {
                TransportRequestState.OPEN, TransportRequestState.ASSIGNED
            }:
                request.state = TransportRequestState.IN_PROGRESS
                source_buffer = self.buffers[request.source_location]
                if unit.id in source_buffer.contents:
                    source_buffer.remove(unit.id)
                source_machine = self.machines.get(request.source_location)
                if source_machine and source_machine.current_material_id == unit.id:
                    source_machine.current_material_id = None
                    source_machine.state = MachineState.WAITING_MATERIAL
                unit.current_location = None
                unit.state = MaterialUnitState.IN_TRANSIT
                self._trace(unit, "PICKED_UP", request.source_location, None,
                            robot_id=task.assigned_robot_id, request_id=request.id, task_id=task.id)
            if task.state == TaskState.COMPLETED and request.state != TransportRequestState.COMPLETED:
                self._complete_request(request, task)

    def _complete_request(self, request: TransportRequest, task: MaterialTask) -> None:
        unit = self.materials[request.material_unit_id]
        request.state = TransportRequestState.COMPLETED
        request.completed_time = task.completed_time
        unit.active_request_id = None
        unit.current_location = request.destination_location
        if request.destination_location in {"OUT_A", "OUT_B"}:
            self.buffers[request.destination_location].receive(request.id, unit.id)
            self.buffers[request.destination_location].remove(unit.id)
            unit.state = MaterialUnitState.SHIPPED
            self.work_orders[unit.work_order_id].complete_unit()
            self._trace(unit, "SHIPPED", request.source_location, request.destination_location,
                        robot_id=task.assigned_robot_id, request_id=request.id, task_id=task.id)
        else:
            self.buffers[request.destination_location].receive(request.id, unit.id)
            unit.state = MaterialUnitState.AT_PROCESS
            self._trace(unit, "DELIVERED", request.source_location, request.destination_location,
                        robot_id=task.assigned_robot_id, request_id=request.id, task_id=task.id)

    def _update_machines(self, delta_time: float) -> None:
        for machine in self.machines.values():
            if machine.state == MachineState.WAITING_MATERIAL:
                if self.buffers[machine.station_id].contents:
                    material_id = self.buffers[machine.station_id].contents[0]
                    self.buffers[machine.station_id].remove(material_id)
                    unit = self.materials[material_id]
                    machine.current_material_id = material_id
                    machine.remaining_time = machine.processing_time
                    machine.state = MachineState.PROCESSING
                    unit.state = MaterialUnitState.PROCESSING
                    unit.current_location = machine.station_id
                    self._trace(unit, "PROCESSING_STARTED", machine.station_id, machine.station_id)
                else:
                    machine.starvation_time += delta_time
            elif machine.state == MachineState.PROCESSING:
                machine.remaining_time -= delta_time
                if machine.remaining_time <= 1e-12:
                    unit = self.materials[machine.current_material_id]
                    machine.remaining_time = 0.0
                    machine.state = MachineState.WAITING_UNLOAD
                    machine.completed_cycles += 1
                    unit.state = MaterialUnitState.WAITING_TRANSFER
                    self._trace(unit, "PROCESSING_COMPLETED", machine.station_id, machine.station_id)
            elif machine.state == MachineState.WAITING_UNLOAD:
                unit = self.materials[machine.current_material_id]
                if unit.active_request_id is None:
                    priority = (TransportPriority.NORMAL if machine.request_type != TransportRequestType.OUTBOUND_MOVE
                                else TransportPriority.LOW)
                    self._create_request(unit, machine.next_station_id, machine.request_type,
                                         priority, "PROCESS_COMPLETE")
                machine.blocking_time += delta_time

    def update(self, delta_time: float) -> None:
        if delta_time < 0:
            raise ValueError("delta_time cannot be negative")
        if not self.running or delta_time == 0:
            return
        self._issue_required_requests()
        self.factory.update(delta_time)
        self.elapsed_time = self.factory.elapsed_time
        self._sync_requests()
        self._update_machines(delta_time)
        self._issue_required_requests()
        self.validate_production_integrity()

    def pause(self) -> None:
        self.running = False
        self.factory.pause()

    def start(self) -> None:
        self.running = True
        self.factory.start()

    def reset(self) -> None:
        self.factory.reset()
        self.__init__(self.factory, target_per_product=self.target_per_product)

    def validate_safety(self) -> None:
        self.factory.validate_safety()
        self.validate_production_integrity()

    def validate_production_integrity(self) -> None:
        locations: dict[str, str] = {}
        for buffer in self.buffers.values():
            if buffer.occupied > buffer.capacity or buffer.occupied < 0:
                self.inventory_accuracy_errors += 1
                raise AssertionError("Buffer capacity invariant failed")
            for material_id in buffer.contents:
                if material_id in locations:
                    self.inventory_accuracy_errors += 1
                    raise AssertionError("Material exists in two buffers")
                locations[material_id] = buffer.station_id
        for machine in self.machines.values():
            if machine.current_material_id:
                if machine.current_material_id in locations:
                    self.inventory_accuracy_errors += 1
                    raise AssertionError("Material exists in buffer and machine")
                locations[machine.current_material_id] = machine.id
        for unit in self.materials.values():
            if unit.state == MaterialUnitState.IN_TRANSIT and unit.current_location is not None:
                raise AssertionError("In-transit material has a fixed location")
            if unit.state == MaterialUnitState.PROCESSING:
                if not any(machine.current_material_id == unit.id for machine in self.machines.values()):
                    raise AssertionError("Processing material is not in a machine")

    @property
    def production_metrics(self) -> ProductionMetrics:
        completed = sum(order.completed_quantity for order in self.work_orders.values())
        target = sum(order.target_quantity for order in self.work_orders.values())
        completed_requests = [r for r in self.requests.values() if r.state == TransportRequestState.COMPLETED]
        lead = [r.completed_time - r.requested_time for r in completed_requests]
        on_time = sum(r.completed_time <= r.due_time for r in completed_requests)
        return ProductionMetrics(
            completed, target, completed / max(self.elapsed_time, 1e-12) * 60.0,
            sum(m.starvation_time for m in self.machines.values()),
            sum(m.blocking_time for m in self.machines.values()),
            sum(lead) / len(lead) if lead else 0.0,
            on_time / len(completed_requests) if completed_requests else 0.0,
            sum(unit.state not in {MaterialUnitState.SHIPPED, MaterialUnitState.AVAILABLE}
                for unit in self.materials.values()),
            sum(buffer.occupied for buffer in self.buffers.values()),
            sum(buffer.capacity for buffer in self.buffers.values()),
            self.inventory_accuracy_errors, len(self.requests), len(completed_requests),
            sum(r.state == TransportRequestState.OPEN for r in self.requests.values()),
            sum(r.state in {TransportRequestState.ASSIGNED, TransportRequestState.IN_PROGRESS}
                for r in self.requests.values()),
        )

    def material_trace(self, material_id: str) -> tuple[MaterialTraceEvent, ...]:
        return tuple(event for event in self.trace_events if event.material_unit_id == material_id)
