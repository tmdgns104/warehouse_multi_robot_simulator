from collections import deque

import pytest

from warehouse_sim.facility_layout import MachineBlock, NetworkSegment
from warehouse_sim.graph_planner import graph_astar
from warehouse_sim.lane_graph import LaneEdge, LaneGraph, LaneNode
from warehouse_sim.lane_safety import (
    LANE_SNAP_TOLERANCE,
    BOTTOM_RETURN_CONNECTOR_IDS,
    OBSTACLE_CLEARANCE,
    RectangleObstacle,
    build_safe_lane_graph,
    machine_obstacle,
    machine_obstacles,
    point_inside_obstacle,
    perpendicular_endpoint_gaps,
    reference_driving_segments,
    reference_render_segments,
    reference_visual_only_segments,
    segment_intersects_obstacle,
    snap_lane_gaps,
    unsafe_edges,
    unsafe_nodes,
    validate_lane_graph_safety,
)
from warehouse_sim.reference_scenario import create_reference_layout
from warehouse_sim.reference_traffic_scenario import create_reference_traffic_scenario
from warehouse_sim.render_plan import Primitive, build_render_plan


def component_count(graph):
    remaining = {node.id for node in graph.nodes}
    count = 0
    while remaining:
        count += 1
        seen = {remaining.pop()}
        queue = deque(seen)
        while queue:
            for neighbor in graph.neighbors(queue.popleft()):
                if neighbor.id not in seen:
                    seen.add(neighbor.id)
                    remaining.discard(neighbor.id)
                    queue.append(neighbor.id)
    return count


def test_machine_obstacle_expands_by_entity_clearance():
    obstacle = machine_obstacle(MachineBlock("machine", 10, 20, 30, 40))
    assert OBSTACLE_CLEARANCE == 7.0
    assert obstacle == RectangleObstacle("machine", 3, 13, 47, 67)


def test_point_and_orthogonal_segment_obstacle_geometry():
    obstacle = RectangleObstacle("box", 10, 10, 20, 20)
    assert point_inside_obstacle((15, 15), obstacle)
    assert not point_inside_obstacle((9, 15), obstacle)
    assert segment_intersects_obstacle((0, 15), (30, 15), obstacle)
    assert not segment_intersects_obstacle((0, 5), (30, 5), obstacle)
    with pytest.raises(ValueError):
        segment_intersects_obstacle((0, 0), (30, 30), obstacle)


def test_unsafe_node_and_edge_are_rejected():
    graph = LaneGraph()
    graph.add_node(LaneNode("outside", 0, 15))
    graph.add_node(LaneNode("inside", 15, 15))
    graph.add_edge(LaneEdge("crossing", "outside", "inside", 15))
    obstacles = (RectangleObstacle("box", 10, 10, 20, 20),)
    assert [node.id for node in unsafe_nodes(graph, obstacles)] == ["inside"]
    assert [edge.id for edge in unsafe_edges(graph, obstacles)] == ["crossing"]
    with pytest.raises(ValueError, match="nodes=1 edges=1"):
        validate_lane_graph_safety(graph, obstacles)


def test_reference_machine_crossings_are_relocated_to_free_aisles():
    layout = create_reference_layout()
    obstacles = machine_obstacles(layout)
    segments = {segment.id: segment for segment in reference_driving_segments(layout)}
    assert {segments[name].start[0] for name in ("vertical_3", "vertical_5", "vertical_7")} == {389.0, 481.0, 578.5}
    for name in ("vertical_3", "vertical_5", "vertical_7"):
        segment = segments[name]
        assert not any(segment_intersects_obstacle(segment.start, segment.end, item) for item in obstacles)


def test_small_loop_gaps_snap_but_obstacle_crossing_snap_does_not():
    layout = create_reference_layout()
    segments = {segment.id: segment for segment in reference_driving_segments(layout)}
    assert segments["left_loop_b"].end == (259, 280)
    assert segments["right_loop_b"].start == (932, 280)
    assert LANE_SNAP_TOLERANCE == 2.0

    source = NetworkSegment("source", (0, 5), (8, 5))
    target = NetworkSegment("target", (10, 0), (10, 10))
    obstacle = RectangleObstacle("barrier", 8.5, 4, 9.5, 6)
    snapped = snap_lane_gaps((source, target), (obstacle,))
    assert snapped[0].end == (8, 5)


def test_safe_driving_graph_is_connected_and_routes_around_machines():
    layout = create_reference_layout()
    graph = build_safe_lane_graph(layout)
    obstacles = machine_obstacles(layout)
    assert component_count(graph) == 1
    assert not unsafe_nodes(graph, obstacles)
    assert not unsafe_edges(graph, obstacles)
    route = graph_astar(graph, "lane_389_219", "lane_389_343")
    assert route is not None
    assert "lane_389_311" in route


def test_only_observed_central_aisles_connect_to_bottom_return():
    segments = {segment.id: segment for segment in reference_driving_segments(create_reference_layout())}
    assert BOTTOM_RETURN_CONNECTOR_IDS == {"vertical_5", "vertical_6", "vertical_7", "vertical_8"}
    assert all(segments[name].end[1] == 648 for name in BOTTOM_RETURN_CONNECTOR_IDS)
    assert segments["vertical_4"].end[1] == 618
    assert segments["vertical_9"].end[1] == 618
    tails = {segment.id: segment for segment in reference_visual_only_segments(create_reference_layout())}
    assert tails["visual_tail_vertical_4"].start == (405, 618)
    assert tails["visual_tail_vertical_4"].end == (405, 633)


def test_visual_only_network_style_cannot_be_confused_with_driving_lane():
    layout = create_reference_layout()
    driving_colors = {segment.color for segment in layout.network if segment.drivable}
    visual_colors = {segment.color for segment in layout.network if not segment.drivable}
    assert visual_colors.isdisjoint(driving_colors)
    graph = build_safe_lane_graph(layout)
    rendered = reference_render_segments(layout, graph)
    rendered_driving = rendered[: len(graph.edges)]
    rendered_edges = {frozenset((segment.start, segment.end)) for segment in rendered_driving}
    graph_edges = {
        frozenset((graph.node(edge.source).position, graph.node(edge.target).position))
        for edge in graph.edges
    }
    assert rendered_edges == graph_edges
    assert len(rendered_driving) == len(graph.edges)
    assert all(segment.drivable for segment in rendered_driving)
    assert all(not segment.drivable for segment in rendered[len(graph.edges):])
    assert not perpendicular_endpoint_gaps(reference_driving_segments(layout))
    machine_detail_lines = [
        command for command in build_render_plan(layout)
        if command.primitive == Primitive.LINE and command.width == 2.2
    ]
    assert machine_detail_lines
    assert all(command.fill not in driving_colors for command in machine_detail_lines)


def test_reference_traffic_candidates_and_motion_stay_obstacle_safe():
    scenario = create_reference_traffic_scenario(16, seed=1234)
    for _ in range(600):
        scenario.engine.update(1 / 60)
        scenario.engine.validate_safety()
    assert scenario.engine.metrics.obstacle_penetration_count == 0
    assert scenario.engine.total_completed_trips > 0
