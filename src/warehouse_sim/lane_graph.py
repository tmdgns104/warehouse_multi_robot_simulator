"""Lane graph domain model and conversion from V2 visual network segments."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import hypot
from typing import Dict, Iterable, Iterator, Mapping, Optional

from .facility_layout import NetworkSegment, Point


@dataclass(frozen=True)
class LaneNode:
    id: str
    x: float
    y: float
    node_type: str = "lane"
    metadata: Mapping[str, object] = field(default_factory=dict, compare=False)

    @property
    def position(self) -> Point:
        return (self.x, self.y)


@dataclass(frozen=True)
class LaneEdge:
    id: str
    source: str
    target: str
    length: float
    bidirectional: bool = True
    metadata: Mapping[str, object] = field(default_factory=dict, compare=False)

    def __post_init__(self) -> None:
        if self.source == self.target:
            raise ValueError("Lane edge endpoints must differ")
        if self.length <= 0:
            raise ValueError("Lane edge length must be positive")


@dataclass(frozen=True)
class LaneTraversal:
    edge: LaneEdge
    source: str
    target: str


class LaneGraph:
    def __init__(self) -> None:
        self._nodes: Dict[str, LaneNode] = {}
        self._edges: Dict[str, LaneEdge] = {}
        self._outgoing: Dict[str, list[LaneTraversal]] = {}

    @property
    def nodes(self) -> tuple[LaneNode, ...]:
        return tuple(self._nodes.values())

    @property
    def edges(self) -> tuple[LaneEdge, ...]:
        return tuple(self._edges.values())

    def add_node(self, node: LaneNode) -> None:
        if node.id in self._nodes:
            raise ValueError(f"Duplicate lane node: {node.id}")
        self._nodes[node.id] = node
        self._outgoing[node.id] = []

    def add_edge(self, edge: LaneEdge) -> None:
        if edge.id in self._edges:
            raise ValueError(f"Duplicate lane edge: {edge.id}")
        if edge.source not in self._nodes or edge.target not in self._nodes:
            raise ValueError(f"Unknown endpoint for lane edge: {edge.id}")
        source = self.node(edge.source)
        target = self.node(edge.target)
        geometric_length = hypot(target.x - source.x, target.y - source.y)
        if abs(edge.length - geometric_length) > 1e-6:
            raise ValueError(f"Edge length does not match node coordinates: {edge.id}")
        self._edges[edge.id] = edge
        self._outgoing[edge.source].append(LaneTraversal(edge, edge.source, edge.target))
        if edge.bidirectional:
            self._outgoing[edge.target].append(LaneTraversal(edge, edge.target, edge.source))

    def node(self, node_id: str) -> LaneNode:
        try:
            return self._nodes[node_id]
        except KeyError as error:
            raise KeyError(f"Unknown lane node: {node_id}") from error

    def edge(self, edge_id: str) -> LaneEdge:
        try:
            return self._edges[edge_id]
        except KeyError as error:
            raise KeyError(f"Unknown lane edge: {edge_id}") from error

    def neighbors(self, node_id: str) -> tuple[LaneNode, ...]:
        return tuple(self.node(traversal.target) for traversal in self.traversals(node_id))

    def traversals(self, node_id: str) -> tuple[LaneTraversal, ...]:
        self.node(node_id)
        return tuple(self._outgoing[node_id])

    def traversal(self, source: str, target: str) -> LaneTraversal:
        for traversal in self.traversals(source):
            if traversal.target == target:
                return traversal
        raise KeyError(f"No lane from {source} to {target}")

    def nearest_node(self, point: Point) -> LaneNode:
        if not self._nodes:
            raise ValueError("Cannot search an empty lane graph")
        return min(self._nodes.values(), key=lambda node: hypot(node.x - point[0], node.y - point[1]))

    def network_segments(self) -> tuple[NetworkSegment, ...]:
        """Expose exactly the graph edges that the V3 renderer should draw."""
        return tuple(
            NetworkSegment(
                f"graph_{edge.id}",
                self.node(edge.source).position,
                self.node(edge.target).position,
                width=float(edge.metadata.get("width", 1.0)),
            )
            for edge in self.edges
        )


def _point_id(point: Point) -> str:
    def component(value: float) -> str:
        return str(int(value)) if float(value).is_integer() else str(value).replace(".", "p")
    return f"lane_{component(point[0])}_{component(point[1])}"


def _on_segment(point: Point, segment: NetworkSegment) -> bool:
    x, y = point
    min_x, max_x = sorted((segment.start[0], segment.end[0]))
    min_y, max_y = sorted((segment.start[1], segment.end[1]))
    return min_x <= x <= max_x and min_y <= y <= max_y and (
        (segment.start[0] == segment.end[0] == x)
        or (segment.start[1] == segment.end[1] == y)
    )


def lane_graph_from_segments(segments: Iterable[NetworkSegment]) -> LaneGraph:
    """Split orthogonal V2 lines at intersections into a routable graph."""
    segments = tuple(segments)
    points_by_segment = {segment.id: {segment.start, segment.end} for segment in segments}
    for index, first in enumerate(segments):
        first_vertical = first.start[0] == first.end[0]
        for second in segments[index + 1 :]:
            second_vertical = second.start[0] == second.end[0]
            if first_vertical == second_vertical:
                # Endpoints on overlapping/meeting collinear segments are enough
                # to split both without manufacturing an infinite intersection.
                for point in (first.start, first.end, second.start, second.end):
                    if _on_segment(point, first) and _on_segment(point, second):
                        points_by_segment[first.id].add(point)
                        points_by_segment[second.id].add(point)
                continue
            vertical, horizontal = (first, second) if first_vertical else (second, first)
            intersection = (vertical.start[0], horizontal.start[1])
            if _on_segment(intersection, vertical) and _on_segment(intersection, horizontal):
                points_by_segment[vertical.id].add(intersection)
                points_by_segment[horizontal.id].add(intersection)

    graph = LaneGraph()
    all_points = sorted({point for points in points_by_segment.values() for point in points}, key=lambda p: (p[1], p[0]))
    for point in all_points:
        graph.add_node(LaneNode(_point_id(point), *point, "intersection" if sum(_on_segment(point, segment) for segment in segments) > 1 else "endpoint"))

    seen_pairs = set()
    edge_number = 0
    for segment in segments:
        vertical = segment.start[0] == segment.end[0]
        ordered = sorted(points_by_segment[segment.id], key=lambda p: p[1] if vertical else p[0])
        for start, target in zip(ordered, ordered[1:]):
            pair = frozenset((start, target))
            if pair in seen_pairs or start == target:
                continue
            seen_pairs.add(pair)
            source_id, target_id = _point_id(start), _point_id(target)
            length = hypot(target[0] - start[0], target[1] - start[1])
            graph.add_edge(LaneEdge(f"edge_{edge_number:03d}", source_id, target_id, length, True, {"source_segment": segment.id, "width": segment.width}))
            edge_number += 1
    return graph
