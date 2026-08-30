import pytest

from warehouse_sim.factory import (
    FactoryConfig,
    FactoryProfile,
    FactoryTaskGenerator,
    factory_config_for_profile,
)
from warehouse_sim.graph_planner import graph_astar
from warehouse_sim.lane_safety import driving_obstacles, point_inside_obstacle
from warehouse_sim.reference_factory_scenario import create_reference_factory_scenario
from warehouse_sim.task_manager import (
    FactoryTaskManager,
    LoadState,
    MaterialLoad,
    MaterialTask,
    RobotWorkState,
    TaskState,
)


def make_task_manager():
    manager = FactoryTaskManager()
    task = MaterialTask("JOB-1", "SOURCE", "DEST", "LOAD-1", created_time=0)
    load = MaterialLoad("LOAD-1", LoadState.AT_SOURCE, "SOURCE", None, "JOB-1")
    manager.create_task(task, load)
    return manager, task, load


def advance(engine, seconds, step=1 / 30):
    for _ in range(round(seconds / step)):
        engine.update(step)
        engine.validate_safety()


def test_factory_task_queue_priority_assignment_and_transition_guards():
    manager, task, load = make_task_manager()
    high = MaterialTask("JOB-2", "SOURCE", "DEST", "LOAD-2", priority=3, created_time=1)
    manager.create_task(high, MaterialLoad("LOAD-2", LoadState.AT_SOURCE, "SOURCE", None, "JOB-2"))
    assert [item.id for item in manager.queued] == ["JOB-2", "JOB-1"]
    with pytest.raises(ValueError, match="Invalid task transition"):
        manager.transition(task, TaskState.PICKING, 1)
    manager.assign(task, "M01", 1)
    manager.reserve_load(task)
    manager.transition(task, TaskState.MOVING_TO_SOURCE, 1)
    assert task.assigned_robot_id == "M01"
    assert load.state == LoadState.RESERVED


def test_pickup_and_drop_require_valid_lifecycle_and_preserve_load_ownership():
    manager, task, load = make_task_manager()
    manager.assign(task, "M01", 1)
    manager.reserve_load(task)
    with pytest.raises(ValueError, match="PICKING"):
        manager.pickup(task, "M01", 2)
    manager.transition(task, TaskState.MOVING_TO_SOURCE, 1)
    manager.transition(task, TaskState.PICKING, 2)
    manager.pickup(task, "M01", 4)
    assert load.state == LoadState.ON_ROBOT
    assert load.carried_by_robot_id == "M01"
    manager.transition(task, TaskState.MOVING_TO_DESTINATION, 4)
    with pytest.raises(ValueError, match="DROPPING"):
        manager.drop(task, "M01")
    manager.transition(task, TaskState.DROPPING, 5)
    manager.drop(task, "M01")
    manager.transition(task, TaskState.COMPLETED, 7)
    assert load.state == LoadState.AT_DESTINATION
    assert load.current_station_id == "DEST"
    assert load.carried_by_robot_id is None
    manager.validate_load_integrity()


def test_task_generator_is_seeded_and_uses_only_material_flow_links():
    flows = (("A", "B", "C"), ("D", "E"))
    first = FactoryTaskGenerator(flows, seed=44)
    second = FactoryTaskGenerator(flows, seed=44)
    sequence_a = [first.create(index)[0] for index in range(10)]
    sequence_b = [second.create(index)[0] for index in range(10)]
    assert [
        (task.source_station_id, task.destination_station_id, task.priority)
        for task in sequence_a
    ] == [
        (task.source_station_id, task.destination_station_id, task.priority)
        for task in sequence_b
    ]
    valid = {("A", "B"), ("B", "C"), ("D", "E")}
    assert all((task.source_station_id, task.destination_station_id) in valid for task in sequence_a)


def test_factory_service_points_are_safe_graph_nodes_and_flows_are_distributed():
    scenario = create_reference_factory_scenario(4, seed=1234)
    obstacles = driving_obstacles(scenario.layout)
    assert {station.role for station in scenario.engine.stations.values()} >= {
        "INPUT", "PROCESS_A", "PROCESS_B", "INSPECTION", "BUFFER", "OUTPUT"
    }
    for station in scenario.engine.stations.values():
        node = scenario.graph.node(station.service_node_id)
        assert len(scenario.graph.neighbors(node.id)) >= 2
        assert not any(point_inside_obstacle(node.position, obstacle) for obstacle in obstacles)
    for flow in scenario.engine.flows:
        for source, destination in zip(flow, flow[1:]):
            source_node = scenario.engine.stations[source].service_node_id
            destination_node = scenario.engine.stations[destination].service_node_id
            assert graph_astar(scenario.graph, source_node, destination_node) is not None


def test_factory_pickup_drop_timers_complete_task_and_return_robot_idle():
    config = FactoryConfig(pickup_duration=0.25, drop_duration=0.25, queue_target=1, max_active_tasks=1)
    scenario = create_reference_factory_scenario(2, seed=9, config=config)
    advance(scenario.engine, 120)
    manager = scenario.engine.task_manager
    assert manager.completed
    completed = manager.completed[0]
    load = manager.loads[completed.load_id]
    assert completed.pickup_time is not None
    assert completed.completed_time > completed.pickup_time > completed.assigned_time
    assert load.state == LoadState.AT_DESTINATION
    assert load.current_station_id == completed.destination_station_id
    assert any(state in (RobotWorkState.IDLE, RobotWorkState.RETURNING) for state in scenario.engine.work_states.values())
    event_names = [event.event for event in manager.events if event.task_id == completed.id]
    assert event_names == [
        "QUEUED", "ASSIGNED", "MOVING_TO_SOURCE", "PICKING",
        "MOVING_TO_DESTINATION", "DROPPING", "COMPLETED",
    ]


def test_factory_continuously_generates_and_assigns_next_tasks_without_random_goals():
    config = FactoryConfig(pickup_duration=0.1, drop_duration=0.1, queue_target=2, max_active_tasks=2)
    scenario = create_reference_factory_scenario(3, seed=12, config=config)
    initial_created = scenario.engine.factory_metrics.tasks_created
    advance(scenario.engine, 180)
    metrics = scenario.engine.factory_metrics
    assert metrics.tasks_completed > 1
    assert metrics.tasks_created > initial_created
    assert metrics.tasks_queued == config.queue_target
    assert scenario.engine.traffic.looping is False
    assert all(task.source_station_id != task.destination_station_id for task in scenario.engine.task_manager.tasks.values())


def test_sixteen_robot_factory_keeps_traffic_and_load_invariants():
    scenario = create_reference_factory_scenario(16, seed=1234)
    advance(scenario.engine, 30)
    factory = scenario.engine.factory_metrics
    traffic = scenario.engine.traffic.metrics
    assert factory.tasks_created > 0
    assert factory.tasks_completed > 0
    assert 0 < factory.robot_utilization < 1
    assert factory.idle_robot_count >= 1
    assert factory.failed_tasks == 0
    assert traffic.head_on_conflict_count == 0
    assert traffic.deadlock_count == 0
    assert traffic.obstacle_penetration_count == 0
    scenario.engine.task_manager.validate_load_integrity()


def test_factory_reset_restores_deterministic_idle_queue():
    scenario = create_reference_factory_scenario(4, seed=88)
    initial_tasks = [
        (task.source_station_id, task.destination_station_id, task.priority)
        for task in scenario.engine.task_manager.queued
    ]
    advance(scenario.engine, 10)
    scenario.engine.reset()
    reset_tasks = [
        (task.source_station_id, task.destination_station_id, task.priority)
        for task in scenario.engine.task_manager.queued
    ]
    assert reset_tasks == initial_tasks
    assert all(state == RobotWorkState.IDLE for state in scenario.engine.work_states.values())
    assert scenario.engine.elapsed_time == 0


def test_station_usage_is_phase_aware_instead_of_reserving_both_ends():
    scenario = create_reference_factory_scenario(2, seed=4, config=FactoryConfig(queue_target=1, max_active_tasks=1))
    engine = scenario.engine
    task = engine.task_manager.queued[0]
    engine.task_manager.assign(task, "M01", 0)
    engine.task_manager.reserve_load(task)
    engine.task_manager.transition(task, TaskState.MOVING_TO_SOURCE, 0)
    users = engine._station_users()
    assert users == {task.source_station_id: task.id}
    engine.task_manager.transition(task, TaskState.PICKING, 1)
    engine.task_manager.transition(task, TaskState.MOVING_TO_DESTINATION, 2)
    users = engine._station_users()
    assert users == {task.destination_station_id: task.id}


def test_destination_capacity_blocks_second_task_until_first_releases_it():
    scenario = create_reference_factory_scenario(4, seed=5, config=FactoryConfig(queue_target=2, max_active_tasks=2))
    engine = scenario.engine
    first, second = engine.task_manager.queued
    second.destination_station_id = first.destination_station_id
    for index, task in enumerate((first, second), start=1):
        engine.task_manager.assign(task, f"M0{index}", 0)
        engine.task_manager.reserve_load(task)
        engine.task_manager.transition(task, TaskState.MOVING_TO_SOURCE, 0)
        engine.task_manager.transition(task, TaskState.PICKING, 1)
    engine.task_manager.transition(first, TaskState.MOVING_TO_DESTINATION, 2)
    assert first.destination_station_id in engine._station_users()
    assert second.destination_station_id in engine._station_users(exclude_task_id=second.id)
    engine.task_manager.transition(first, TaskState.DROPPING, 3)
    engine.task_manager.transition(first, TaskState.COMPLETED, 4)
    assert second.destination_station_id not in engine._station_users(exclude_task_id=second.id)


def test_direct_handoff_reuses_completed_robot_without_parking_trip():
    config = FactoryConfig(pickup_duration=0.1, drop_duration=0.1, queue_target=12, max_active_tasks=10)
    scenario = create_reference_factory_scenario(8, seed=1234, config=config)
    advance(scenario.engine, 100)
    metrics = scenario.engine.factory_metrics
    assert metrics.direct_task_handoffs > 0
    assert metrics.direct_task_handoffs < metrics.tasks_completed
    assert metrics.parking_returns > 0


def test_utilization_separates_productive_repositioning_and_idle_time():
    scenario = create_reference_factory_scenario(8, seed=8, profile=FactoryProfile.BUSY)
    advance(scenario.engine, 60)
    metrics = scenario.engine.factory_metrics
    assert metrics.productive_utilization > 0
    assert metrics.repositioning_utilization > 0
    assert metrics.idle_ratio > 0
    assert metrics.robot_utilization == pytest.approx(
        metrics.productive_utilization + metrics.repositioning_utilization
    )
    assert metrics.productive_utilization + metrics.repositioning_utilization + metrics.idle_ratio == pytest.approx(1)


def test_busy_profile_improves_task_participation_without_random_motion():
    assert factory_config_for_profile("busy").queue_target == 12
    scenario = create_reference_factory_scenario(16, seed=1234, profile="busy")
    advance(scenario.engine, 60)
    metrics = scenario.engine.factory_metrics
    assert metrics.productive_utilization > 0.30
    assert metrics.average_active_robots > 5
    assert metrics.queued_but_dispatchable == 0
    assert metrics.queued_but_blocked == metrics.tasks_queued
    assert metrics.assignment_blocked_station > 0
    assert metrics.assignment_blocked_no_route == 0
    assert scenario.engine.traffic.looping is False


def test_robot_is_never_double_assigned_during_busy_factory_operation():
    scenario = create_reference_factory_scenario(16, seed=27, profile="busy")
    advance(scenario.engine, 90)
    assigned = [
        task.assigned_robot_id for task in scenario.engine.task_manager.active
        if task.assigned_robot_id is not None
    ]
    assert len(assigned) == len(set(assigned))
    scenario.engine.task_manager.validate_load_integrity()
