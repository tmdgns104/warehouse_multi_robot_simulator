from collections import deque

import pytest

from warehouse_sim.facility_layout import MachineBlock, NetworkSegment, Station
from warehouse_sim.graph_planner import graph_astar
from warehouse_sim.lane_graph import LaneEdge, LaneGraph, LaneNode
from warehouse_sim.lane_safety import (
    LANE_SNAP_TOLERANCE,
    OBSTACLE_CLEARANCE,
    RectangleObstacle,
    build_safe_lane_graph,
    candidate_grid_segments,
    driving_obstacles,
    machine_obstacle,
    machine_obstacles,
    point_inside_obstacle,
    perpendicular_endpoint_gaps,
    reference_driving_segments,
    reference_render_segments,
    reference_visual_only_segments,
    segment_intersects_obstacle,
    snap_lane_gaps,
    station_obstacle,
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
    station = station_obstacle(Station("station", 10, 20, 30, 40, (0, 0, 0)))
    assert station == RectangleObstacle("station", 3, 13, 47, 67)


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


def test_candidate_grid_is_pruned_around_machine_and_station_obstacles():
    layout = create_reference_layout()
    candidates = candidate_grid_segments(layout)
    assert any(segment.start == (365, 112) and segment.end == (365, 648) for segment in candidates)
    obstacles = driving_obstacles(layout)
    surviving = reference_driving_segments(layout)
    assert all(
        not segment_intersects_obstacle(segment.start, segment.end, obstacle)
        for segment in surviving
        for obstacle in obstacles
    )
    assert any(segment.id.startswith("grid_v_3_part_") for segment in surviving)


def test_small_gap_snap_cannot_cross_obstacle():
    assert LANE_SNAP_TOLERANCE == 2.0

    source = NetworkSegment("source", (0, 5), (8, 5))
    target = NetworkSegment("target", (10, 0), (10, 10))
    obstacle = RectangleObstacle("barrier", 8.5, 4, 9.5, 6)
    snapped = snap_lane_gaps((source, target), (obstacle,))
    assert snapped[0].end == (8, 5)


def test_safe_driving_graph_is_connected_and_routes_around_machines():
    layout = create_reference_layout()
    graph = build_safe_lane_graph(layout)
    obstacles = driving_obstacles(layout)
    assert component_count(graph) == 1
    assert not unsafe_nodes(graph, obstacles)
    assert not unsafe_edges(graph, obstacles)
    route = graph_astar(graph, "lane_365_219", "lane_365_311")
    assert route is not None
    assert len(route) > 2
    assert any(graph.node(node_id).x != 365 for node_id in route)


def test_bottom_grid_connects_each_safe_vertical_to_return_rail():
    layout = create_reference_layout()
    graph = build_safe_lane_graph(layout)
    bottom_nodes = {node.x for node in graph.nodes if node.y == 648}
    candidate_x = {
        segment.start[0] for segment in candidate_grid_segments(layout)
        if segment.start[0] == segment.end[0]
    }
    assert bottom_nodes == candidate_x
    visual_ids = {segment.id for segment in reference_visual_only_segments(layout)}
    assert visual_ids == {"top_cap_a", "top_cap_b", "top_cap_c"}


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
    for _ in range(1800):
        scenario.engine.update(1 / 60)
        scenario.engine.validate_safety()
    assert scenario.engine.metrics.obstacle_penetration_count == 0
    assert scenario.engine.total_completed_trips > 0
