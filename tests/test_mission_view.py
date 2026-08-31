from pathlib import Path

import pytest

from warehouse_sim.mission_view import (
    MISSION_LABELS, all_robot_missions, mission_counts, robot_mission_view,
)
from warehouse_sim.production import TransportRequestType
from warehouse_sim.reference_production_scenario import create_reference_production_scenario
from warehouse_sim.reference_renderer import render_factory_with_pillow


def advance(engine, seconds, step=1 / 30):
    for _ in range(round(seconds / step)):
        engine.update(step)


@pytest.mark.parametrize(("request_type", "label"), (
    (TransportRequestType.LINE_SUPPLY, "SUPPLY"),
    (TransportRequestType.WIP_TRANSFER, "WIP"),
    (TransportRequestType.QC_TRANSFER, "QC"),
    (TransportRequestType.OUTBOUND_MOVE, "OUT"),
))
def test_business_mission_label_mapping(request_type, label):
    assert MISSION_LABELS[request_type] == label


def test_active_and_idle_robot_projections_do_not_invent_missions():
    engine = create_reference_production_scenario(4, target_per_product=2).engine
    advance(engine, 1)
    views = all_robot_missions(engine)
    assert any(view.mission == "SUPPLY" for view in views)
    assert all(view.mission is None for view in views if engine.robot_tasks[view.robot_id] is None)


def test_mission_links_request_lot_order_and_endpoints():
    engine = create_reference_production_scenario(4, target_per_product=2).engine
    advance(engine, 1)
    view = next(view for view in all_robot_missions(engine) if view.mission)
    request = engine.requests[view.request_id]
    assert view.task_id == request.material_task_id
    assert view.lot_id == engine.materials[request.material_unit_id].lot_id
    assert view.work_order_id == request.work_order_id
    assert (view.source, view.destination) == (request.source_location, request.destination_location)


def test_cargo_badge_uses_real_load_ownership_and_disappears_after_completion():
    engine = create_reference_production_scenario(8, target_per_product=2).engine
    assert not any(view.has_cargo for view in all_robot_missions(engine))
    for _ in range(4000):
        engine.update(1 / 30)
        cargo = [view for view in all_robot_missions(engine) if view.has_cargo]
        if cargo:
            break
    assert cargo
    view = cargo[0]
    task = engine.factory.task_manager.tasks[view.task_id]
    load = engine.factory.task_manager.loads[task.load_id]
    assert load.carried_by_robot_id == view.robot_id
    for _ in range(4000):
        engine.update(1 / 30)
        if task.completed_time is not None:
            break
    assert task.completed_time is not None
    assert not robot_mission_view(engine, view.robot_id).has_cargo


def test_selected_projection_uses_actual_remaining_route_and_station_nodes():
    engine = create_reference_production_scenario(4, target_per_product=2).engine
    advance(engine, 5)
    view = next(view for view in all_robot_missions(engine) if view.mission)
    entity = next(entity for entity in engine.entities if entity.id == view.robot_id)
    assert view.route_node_ids == tuple(entity.route[entity.route_index:])
    assert view.source_node_id == engine.stations[view.source].service_node_id
    assert view.destination_node_id == engine.stations[view.destination].service_node_id


def test_mission_counts_are_derived_from_request_lifecycle():
    engine = create_reference_production_scenario(16, target_per_product=3).engine
    advance(engine, 180)
    rows = {row.mission: row for row in mission_counts(engine)}
    assert set(rows) == {"SUPPLY", "WIP", "QC", "OUT"}
    assert all(row.created >= row.assigned >= row.completed for row in rows.values())
    assert rows["SUPPLY"].completed > 0
    assert rows["OUT"].completed > 0


def test_rendering_normal_debug_and_selected_views_does_not_mutate_state(tmp_path: Path):
    scenario = create_reference_production_scenario(8, target_per_product=2)
    advance(scenario.engine, 60)
    before = (scenario.engine.elapsed_time, scenario.engine.production_metrics,
              tuple((request.id, request.state) for request in scenario.engine.requests.values()),
              tuple((entity.id, entity.current_node, entity.route_index) for entity in scenario.engine.entities))
    active = next(view.robot_id for view in all_robot_missions(scenario.engine) if view.mission)
    render_factory_with_pillow(scenario.layout, scenario.engine, tmp_path / "normal.png")
    render_factory_with_pillow(scenario.layout, scenario.engine, tmp_path / "debug.png", debug=True)
    render_factory_with_pillow(scenario.layout, scenario.engine, tmp_path / "selected.png",
                               selected_robot_id=active)
    after = (scenario.engine.elapsed_time, scenario.engine.production_metrics,
             tuple((request.id, request.state) for request in scenario.engine.requests.values()),
             tuple((entity.id, entity.current_node, entity.route_index) for entity in scenario.engine.entities))
    assert before == after
    assert all((tmp_path / name).stat().st_size > 0
               for name in ("normal.png", "debug.png", "selected.png"))


def test_v54_300_second_result_and_safety_are_unchanged():
    engine = create_reference_production_scenario(16, seed=1234).engine
    advance(engine, 300, step=1 / 60)
    metrics = engine.production_metrics
    traffic = engine.factory.traffic.metrics
    assert (metrics.production_completed_units, metrics.transport_requests_created,
            metrics.transport_requests_completed) == (6, 22, 20)
    assert metrics.average_transport_lead_time == pytest.approx(34.035, abs=0.001)
    assert (traffic.head_on_conflict_count, traffic.deadlock_count,
            traffic.obstacle_penetration_count) == (0, 0, 0)
