import math

from warehouse_sim.lane_graph import LaneEdge, LaneGraph, LaneNode
from warehouse_sim.motion import LaneMobileEntity, MotionState
from warehouse_sim.reference_traffic_scenario import (
    DEFAULT_ENTITY_COUNT,
    create_reference_traffic_scenario,
)
from warehouse_sim.traffic import TrafficController
from warehouse_sim.traffic_simulation import TrafficMotionEngine


def intersection_graph():
    graph = LaneGraph()
    for node_id, x, y in (
        ("L", 0, 10), ("C", 10, 10), ("R", 20, 10),
        ("U", 10, 0), ("D", 10, 20), ("X", 40, 40),
    ):
        graph.add_node(LaneNode(node_id, x, y))
    for edge_id, source, target in (
        ("LC", "L", "C"), ("CR", "C", "R"),
        ("UC", "U", "C"), ("CD", "C", "D"),
    ):
        graph.add_edge(LaneEdge(edge_id, source, target, 10, True))
    return graph


def test_node_reservation_rejects_second_owner():
    controller = TrafficController()
    controller.occupy_node("M1", "A")
    try:
        controller.occupy_node("M2", "A")
    except ValueError as error:
        assert "occupied" in str(error)
    else:
        raise AssertionError("same node reservation must fail")


def test_edge_and_target_are_reserved_and_released():
    graph = intersection_graph()
    controller = TrafficController()
    controller.occupy_node("M1", "L")
    decision = controller.request_entry("M1", "L", graph.edge("LC"), "C")
    assert decision.granted
    assert controller.owner_of_edge("LC") == "M1"
    assert controller.owner_of_node("C") == "M1"
    assert controller.owner_of_node("L") is None
    controller.complete_edge("M1", "LC", "C")
    assert controller.owner_of_edge("LC") is None
    assert controller.owner_of_node("C") == "M1"


def test_head_on_edge_request_is_denied():
    graph = intersection_graph()
    controller = TrafficController()
    controller.occupy_node("M1", "L")
    assert controller.request_entry("M1", "L", graph.edge("LC"), "C").granted
    decision = controller.request_entry("M2", "C", graph.edge("LC"), "L")
    assert not decision.granted
    assert "edge" in decision.reason
    assert controller.conflict_count == 1


def test_same_intersection_priority_and_waiting_state():
    graph = intersection_graph()
    first = LaneMobileEntity("M1", "L", "C", 5)
    second = LaneMobileEntity("M2", "U", "C", 5)
    second.waiting_count = 3
    engine = TrafficMotionEngine(graph, [first, second], looping=False)
    # Constructor preserves the explicit accumulated wait for priority.
    second.waiting_count = 3
    engine.update(0.01)
    assert second.current_edge == "UC"
    assert first.state == MotionState.WAITING
    assert first.waiting_count == 1
    assert engine.controller.owner_of_node("C") == "M2"


def test_priority_tie_uses_stable_creation_order():
    graph = intersection_graph()
    first = LaneMobileEntity("M9", "L", "C", 5)
    second = LaneMobileEntity("M1", "U", "C", 5)
    engine = TrafficMotionEngine(graph, [first, second], looping=False)
    engine.update(0.01)
    assert first.current_edge == "LC"
    assert second.state == MotionState.WAITING


def test_blocked_warning_is_observable():
    graph = LaneGraph()
    graph.add_node(LaneNode("A", 0, 0))
    graph.add_node(LaneNode("B", 10, 0))
    graph.add_edge(LaneEdge("AB", "A", "B", 10))
    entities = [
        LaneMobileEntity("M1", "A", "B", 2),
        LaneMobileEntity("M2", "B", "A", 2),
    ]
    engine = TrafficMotionEngine(
        graph, entities, looping=False, blocked_warning_seconds=0.1
    )
    engine.update(0.2)
    assert all(entity.state == MotionState.WAITING for entity in entities)
    assert engine.controller.events
    assert "blocked" in engine.controller.events[0]


def test_no_route_goal_is_safe():
    graph = intersection_graph()
    entity = LaneMobileEntity("M1", "L", "X", 5)
    engine = TrafficMotionEngine(graph, [entity], looping=False)
    assert entity.state == MotionState.NO_ROUTE
    engine.update(1)
    assert entity.position(graph) == (0, 10)


def test_arrival_reassigns_goal_and_continues():
    graph = intersection_graph()
    entity = LaneMobileEntity("M1", "L", "C", 20)
    engine = TrafficMotionEngine(
        graph, [entity], looping=True, seed=7, goal_candidates=("L", "C", "R", "U", "D")
    )
    engine.update(1.0)
    assert engine.total_completed_trips >= 1
    assert entity.completed_trips >= 1
    assert entity.goal_node != "C" or entity.state != MotionState.ARRIVED


def test_one_shot_stops_at_arrival():
    graph = intersection_graph()
    entity = LaneMobileEntity("M1", "L", "C", 20)
    engine = TrafficMotionEngine(graph, [entity], looping=False)
    engine.update(1.0)
    assert entity.state == MotionState.ARRIVED
    completed = engine.total_completed_trips
    engine.update(1.0)
    assert engine.total_completed_trips == completed


def test_reference_scenario_is_seeded_and_has_sixteen_unique_starts():
    first = create_reference_traffic_scenario(seed=99)
    second = create_reference_traffic_scenario(seed=99)
    assert len(first.engine.entities) == DEFAULT_ENTITY_COUNT == 16
    first_pairs = [(entity.current_node, entity.goal_node) for entity in first.engine.entities]
    second_pairs = [(entity.current_node, entity.goal_node) for entity in second.engine.entities]
    assert first_pairs == second_pairs
    assert len({entity.current_node for entity in first.engine.entities}) == 16


def test_invalid_entity_counts_are_rejected():
    for count in (0, -1, 65):
        try:
            create_reference_traffic_scenario(count)
        except ValueError:
            pass
        else:
            raise AssertionError(f"entity count {count} should fail")


def test_long_running_traffic_remains_safe_and_productive():
    scenario = create_reference_traffic_scenario(16, seed=1234)
    seen_waiting = False
    for _ in range(2400):  # 120 simulated seconds at 20 Hz
        scenario.engine.update(0.05)
        scenario.engine.validate_safety()
        seen_waiting |= scenario.engine.metrics.waiting_count > 0
        positions = [
            (round(x, 7), round(y, 7))
            for _, (x, y), _ in scenario.engine.snapshot()
        ]
        assert len(positions) == len(set(positions))
    metrics = scenario.engine.metrics
    assert metrics.total_completed_trips > 0
    assert metrics.reservation_conflicts > 0
    assert seen_waiting
    assert metrics.moving_count + metrics.waiting_count + metrics.arrived_count == 16
