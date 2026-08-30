import math

from warehouse_sim.graph_planner import graph_astar
from warehouse_sim.lane_graph import LaneEdge, LaneGraph, LaneNode


def make_graph():
    graph = LaneGraph()
    for node in (
        LaneNode("A", 0, 0, "station"),
        LaneNode("B", 10, 0, "intersection"),
        LaneNode("C", 10, 10, "station"),
        LaneNode("D", 20, 0),
        LaneNode("X", 50, 50),
    ):
        graph.add_node(node)
    graph.add_edge(LaneEdge("AB", "A", "B", 10, True))
    graph.add_edge(LaneEdge("BC", "B", "C", 10, False))
    graph.add_edge(LaneEdge("BD", "B", "D", 10, True))
    return graph


def test_lane_node_and_edge_registration():
    graph = make_graph()
    assert graph.node("A").position == (0, 0)
    assert graph.edge("AB").source == "A"
    assert math.isclose(graph.edge("AB").length, 10)


def test_neighbor_lookup_and_bidirectional_edge():
    graph = make_graph()
    assert {node.id for node in graph.neighbors("B")} == {"A", "C", "D"}
    assert [node.id for node in graph.neighbors("A")] == ["B"]
    assert graph.traversal("B", "A").edge.id == "AB"


def test_directed_edge_only_allows_source_to_target():
    graph = make_graph()
    assert graph.traversal("B", "C").edge.id == "BC"
    try:
        graph.traversal("C", "B")
    except KeyError:
        pass
    else:
        raise AssertionError("directed edge incorrectly allowed reverse traversal")


def test_graph_astar_route_and_no_route():
    graph = make_graph()
    assert graph_astar(graph, "A", "C") == ["A", "B", "C"]
    assert graph_astar(graph, "A", "X") is None


def test_graph_rejects_length_that_disagrees_with_coordinates():
    graph = LaneGraph()
    graph.add_node(LaneNode("A", 0, 0))
    graph.add_node(LaneNode("B", 3, 4))
    try:
        graph.add_edge(LaneEdge("wrong", "A", "B", 4))
    except ValueError as error:
        assert "length" in str(error)
    else:
        raise AssertionError("invalid geometric length should fail")
