import math

from warehouse_sim.facility_layout import NetworkSegment
from warehouse_sim.lane_graph import LaneGraph, LaneEdge, LaneNode, lane_graph_from_segments
from warehouse_sim.motion import LaneMobileEntity, MotionEngine, MotionState
from warehouse_sim.reference_motion_scenario import create_reference_motion_scenario


def line_graph():
    graph = LaneGraph()
    graph.add_node(LaneNode("A", 0, 0))
    graph.add_node(LaneNode("B", 10, 0))
    graph.add_node(LaneNode("C", 10, 10))
    graph.add_edge(LaneEdge("AB", "A", "B", 10))
    graph.add_edge(LaneEdge("BC", "B", "C", 10))
    return graph


def test_progress_and_edge_interpolation():
    graph = line_graph()
    entity = LaneMobileEntity("M", "A", "C", speed=5)
    engine = MotionEngine(graph, [entity])
    engine.update(1.0)
    assert math.isclose(entity.progress, 0.5)
    assert entity.current_edge == "AB"
    assert entity.position(graph) == (5.0, 0.0)


def test_edge_completion_transitions_to_next_edge():
    graph = line_graph()
    entity = LaneMobileEntity("M", "A", "C", speed=12)
    engine = MotionEngine(graph, [entity])
    engine.update(1.0)
    assert entity.current_node == "B"
    assert entity.current_edge == "BC"
    assert math.isclose(entity.progress, 0.2)
    assert entity.position(graph) == (10.0, 2.0)


def test_destination_arrival_consumes_large_delta_time():
    graph = line_graph()
    entity = LaneMobileEntity("M", "A", "C", speed=8)
    engine = MotionEngine(graph, [entity])
    engine.update(10.0)
    assert entity.state == MotionState.ARRIVED
    assert entity.current_node == "C"
    assert entity.current_edge is None
    assert entity.position(graph) == (10, 10)


def test_motion_is_independent_of_frame_rate():
    graph = line_graph()
    slow_frames = MotionEngine(graph, [LaneMobileEntity("M", "A", "C", 6)])
    fast_frames = MotionEngine(graph, [LaneMobileEntity("M", "A", "C", 6)])
    for _ in range(10):
        slow_frames.update(0.1)
    for _ in range(100):
        fast_frames.update(0.01)
    first = slow_frames.entities[0]
    second = fast_frames.entities[0]
    assert all(
        math.isclose(first_value, second_value)
        for first_value, second_value in zip(first.position(graph), second.position(graph))
    )
    assert math.isclose(first.progress, second.progress)


def test_entity_never_leaves_current_lane_segment():
    graph = line_graph()
    entity = LaneMobileEntity("M", "A", "C", speed=3)
    engine = MotionEngine(graph, [entity])
    for _ in range(70):
        engine.update(0.1)
        x, y = entity.position(graph)
        assert (math.isclose(y, 0) and 0 <= x <= 10) or (
            math.isclose(x, 10) and 0 <= y <= 10
        )


def test_no_route_is_safe():
    graph = line_graph()
    graph.add_node(LaneNode("X", 100, 100))
    entity = LaneMobileEntity("M", "A", "X", speed=5)
    engine = MotionEngine(graph, [entity])
    assert entity.state == MotionState.NO_ROUTE
    engine.update(1.0)
    assert entity.position(graph) == (0, 0)


def test_visual_segments_create_graph_intersections_and_edges():
    graph = lane_graph_from_segments((
        NetworkSegment("horizontal", (0, 5), (10, 5)),
        NetworkSegment("vertical", (5, 0), (5, 10)),
    ))
    center = graph.nearest_node((5, 5))
    assert center.position == (5, 5)
    assert len(graph.neighbors(center.id)) == 4
    assert len(graph.edges) == 4


def test_reference_demo_has_multiple_routed_entities():
    scenario = create_reference_motion_scenario()
    assert len(scenario.engine.entities) >= 4
    assert all(entity.state == MotionState.MOVING for entity in scenario.engine.entities)
    assert all(len(entity.route) > 2 for entity in scenario.engine.entities)
