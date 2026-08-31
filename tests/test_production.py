import pytest

from warehouse_sim.production import (
    MachineState,
    MaterialBuffer,
    MaterialUnitState,
    TransportPriority,
    TransportRequestState,
    TransportRequestType,
    WorkOrder,
    WorkOrderState,
)
from warehouse_sim.reference_production_scenario import create_reference_production_scenario


def advance(engine, seconds, step=1 / 30):
    for _ in range(round(seconds / step)):
        engine.update(step)
        engine.validate_safety()


def test_work_order_starts_counts_units_and_completes_at_target():
    order = WorkOrder("WO", "PRODUCT", 2)
    assert order.state == WorkOrderState.PLANNED
    order.start()
    order.complete_unit()
    assert order.state == WorkOrderState.RUNNING
    order.complete_unit()
    assert order.completed_quantity == 2
    assert order.state == WorkOrderState.COMPLETED
    with pytest.raises(ValueError):
        order.complete_unit()


def test_material_buffer_enforces_capacity_and_membership():
    buffer = MaterialBuffer("B", "S", 1)
    buffer.add("M1")
    assert buffer.occupied == 1 and buffer.free == 0
    with pytest.raises(ValueError, match="capacity"):
        buffer.add("M2")
    with pytest.raises(ValueError, match="not in buffer"):
        buffer.remove("missing")
    buffer.remove("M1")
    assert buffer.occupied == 0


def test_buffer_inbound_reservation_prevents_overbooking():
    buffer = MaterialBuffer("B", "S", 1)
    assert buffer.reserve_inbound("TR-1")
    assert not buffer.reserve_inbound("TR-2")
    buffer.receive("TR-1", "M1")
    assert buffer.contents == ["M1"]


def test_production_demand_creates_traceable_line_supply_requests_and_tasks():
    scenario = create_reference_production_scenario(4, seed=1234, target_per_product=2)
    engine = scenario.engine
    assert len(engine.requests) == 2
    assert {r.request_type for r in engine.requests.values()} == {TransportRequestType.LINE_SUPPLY}
    for request in engine.requests.values():
        task = engine.factory.task_manager.tasks[request.material_task_id]
        assert task.transport_request_id == request.id
        assert request.work_order_id == engine.materials[request.material_unit_id].work_order_id


def test_starved_machine_supply_has_business_priority_and_reason():
    scenario = create_reference_production_scenario(4, seed=1234, target_per_product=2)
    advance(scenario.engine, 1)
    supplies = [r for r in scenario.engine.requests.values()
                if r.request_type == TransportRequestType.LINE_SUPPLY]
    assert supplies
    assert all(r.priority >= TransportPriority.HIGH for r in supplies)
    assert all(r.reason == "PRODUCTION_SUPPLY" for r in supplies)


def test_machine_runs_processing_timer_and_emits_downstream_request():
    scenario = create_reference_production_scenario(8, seed=1234, target_per_product=2)
    advance(scenario.engine, 90)
    assert any(machine.completed_cycles > 0 for machine in scenario.engine.machines.values())
    assert any(request.request_type in {
        TransportRequestType.WIP_TRANSFER,
        TransportRequestType.QC_TRANSFER,
        TransportRequestType.OUTBOUND_MOVE,
    } for request in scenario.engine.requests.values())


def test_transport_request_lifecycle_tracks_robot_task_completion():
    scenario = create_reference_production_scenario(8, seed=1234, target_per_product=2)
    advance(scenario.engine, 90)
    completed = [r for r in scenario.engine.requests.values()
                 if r.state == TransportRequestState.COMPLETED]
    assert completed
    for request in completed:
        task = scenario.engine.factory.task_manager.tasks[request.material_task_id]
        assert task.state.value == "COMPLETED"
        assert request.completed_time == task.completed_time


def test_material_end_to_end_trace_reconstructs_work_order_request_task_and_robot():
    scenario = create_reference_production_scenario(16, seed=1234, target_per_product=2)
    advance(scenario.engine, 180)
    shipped = next(unit for unit in scenario.engine.materials.values()
                   if unit.state == MaterialUnitState.SHIPPED)
    trace = scenario.engine.material_trace(shipped.id)
    assert trace[0].event == "CREATED"
    assert trace[-1].event == "SHIPPED"
    assert any(event.event == "PROCESSING_STARTED" for event in trace)
    assert any(event.robot_id for event in trace)
    assert all(event.work_order_id == shipped.work_order_id for event in trace)
    expected = ({"PROC_A", "QC_A", "OUT_A"} if shipped.work_order_id == "WO-A"
                else {"PROC_B", "BUFFER_B", "OUT_B"})
    assert {event.to_location for event in trace if event.to_location} >= expected


def test_inventory_and_machine_location_invariants_hold_during_operation():
    scenario = create_reference_production_scenario(16, seed=44, target_per_product=3)
    advance(scenario.engine, 120)
    scenario.engine.validate_production_integrity()
    assert scenario.engine.production_metrics.inventory_accuracy_errors == 0
    assert all(0 <= buffer.occupied <= buffer.capacity for buffer in scenario.engine.buffers.values())


def test_machine_starvation_and_blocking_are_caused_by_delivery_flow():
    scenario = create_reference_production_scenario(8, seed=1234, target_per_product=2)
    advance(scenario.engine, 120)
    metrics = scenario.engine.production_metrics
    assert metrics.machine_starvation_time > 0
    assert metrics.machine_blocking_time > 0
    assert all(isinstance(machine.state, MachineState) for machine in scenario.engine.machines.values())


def test_production_metrics_connect_orders_inventory_transport_and_fleet():
    scenario = create_reference_production_scenario(16, seed=1234, target_per_product=3)
    advance(scenario.engine, 180)
    production = scenario.engine.production_metrics
    fleet = scenario.engine.factory_metrics
    assert production.production_completed_units > 0
    assert production.transport_requests_completed > production.production_completed_units
    assert production.wip_count >= 0
    assert production.buffer_occupancy <= production.buffer_capacity
    assert fleet.tasks_completed == production.transport_requests_completed
    assert fleet.actual_motion_ratio > 0


def test_300_second_scenario_completes_full_material_lifecycle_safely():
    scenario = create_reference_production_scenario(16, seed=1234)
    advance(scenario.engine, 300, step=1 / 60)
    production = scenario.engine.production_metrics
    traffic = scenario.engine.factory.traffic.metrics
    assert production.production_completed_units > 0
    assert production.transport_requests_completed > 0
    assert production.inventory_accuracy_errors == 0
    assert traffic.head_on_conflict_count == 0
    assert traffic.deadlock_count == 0
    assert traffic.obstacle_penetration_count == 0


def test_same_seed_production_scenario_is_deterministic():
    first = create_reference_production_scenario(8, seed=91, target_per_product=2)
    second = create_reference_production_scenario(8, seed=91, target_per_product=2)
    advance(first.engine, 90)
    advance(second.engine, 90)
    assert first.engine.production_metrics == second.engine.production_metrics
    assert [(e.event, e.material_unit_id, e.robot_id) for e in first.engine.trace_events] == [
        (e.event, e.material_unit_id, e.robot_id) for e in second.engine.trace_events
    ]
