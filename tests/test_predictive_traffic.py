from warehouse_sim.lane_graph import LaneEdge, LaneGraph, LaneNode
from warehouse_sim.motion import LaneMobileEntity
from warehouse_sim.traffic import TrafficController
from warehouse_sim.traffic_planner import CongestionModel, TrafficZone, traffic_astar
from warehouse_sim.traffic_simulation import TrafficMotionEngine


def diamond_graph():
    graph = LaneGraph()
    for node_id, x, y in (
        ("A", 0, 5), ("B", 10, 0), ("C", 10, 10), ("D", 20, 5)
    ):
        graph.add_node(LaneNode(node_id, x, y))
    length = 125 ** 0.5
    for edge_id, source, target in (
        ("AB", "A", "B"), ("BD", "B", "D"),
        ("AC", "A", "C"), ("CD", "C", "D"),
    ):
        graph.add_edge(LaneEdge(edge_id, source, target, length))
    return graph


def test_predictive_reservation_horizon_and_expiry():
    graph = diamond_graph()
    entity = LaneMobileEntity("M1", "A", "D", 5)
    engine = TrafficMotionEngine(graph, [entity], looping=False)
    engine.update(0.01)
    records = [
        record
        for owners in engine.controller.predictive_reservations.values()
        for record in owners.values()
    ]
    assert records
    assert all(record.owner == "M1" and record.expires_at > 0 for record in records)
    engine.controller.expire_predictions(10)
    assert not engine.controller.predictive_reservations


def test_congestion_cost_selects_less_congested_route():
    graph = diamond_graph()
    controller = TrafficController()
    controller.occupy_node("OTHER", "B")
    model = CongestionModel(graph, controller)
    assert traffic_astar(graph, "A", "D", model, "M1") == ["A", "C", "D"]


def test_zone_capacity_adds_route_penalty():
    graph = diamond_graph()
    controller = TrafficController()
    controller.occupy_node("OTHER", "B")
    zone = TrafficZone("bottleneck", frozenset({"B"}), 1)
    model = CongestionModel(graph, controller, (zone,))
    via_b = graph.traversal("A", "B")
    via_c = graph.traversal("A", "C")
    assert model.traversal_cost(via_b, "M1") > model.traversal_cost(via_c, "M1")


def test_dynamic_reroute_obeys_cooldown_and_improvement():
    graph = diamond_graph()
    entity = LaneMobileEntity("M1", "A", "D", 5)
    engine = TrafficMotionEngine(graph, [entity], looping=False)
    assert entity.route == ["A", "B", "D"]
    engine.controller.occupy_node("OTHER", "B")
    entity.last_reroute_time = 0
    engine.elapsed_time = 1
    assert not engine._try_reroute(entity)
    engine.elapsed_time = 4
    assert engine._try_reroute(entity)
    assert entity.route == ["A", "C", "D"]
    assert entity.reroute_count == 1


def test_speed_coordinator_slows_before_predicted_conflict():
    graph = diamond_graph()
    entity = LaneMobileEntity("M1", "A", "D", 20)
    engine = TrafficMotionEngine(graph, [entity], looping=False)
    entity.route = ["A", "B", "D"]
    entity.route_index = 0
    entity.current_speed = entity.preferred_speed
    engine.controller.refresh_predictions("OTHER", [("edge", "BD", 0.2)], ttl=10)
    engine._coordinate_speed(entity, 0.5)
    assert entity.target_speed < entity.preferred_speed
    assert entity.current_speed < entity.preferred_speed
    assert entity.current_speed >= entity.minimum_moving_speed


def test_wait_for_cycle_is_detected_before_grant():
    controller = TrafficController()
    controller.wait_for["M2"] = "M1"
    assert controller.would_create_wait_cycle("M1", "M2")
    assert not controller.would_create_wait_cycle("M3", "M2")
