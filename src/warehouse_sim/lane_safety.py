"""Obstacle-aware construction and validation for the reference driving graph."""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Iterable

from .facility_layout import FacilityLayout, MachineBlock, NetworkSegment, Point, Station
from .lane_graph import LaneEdge, LaneGraph, lane_graph_from_segments

# V4 entities are at most 11 px wide.  Their 5.5 px half-footprint plus 1.5 px
# of drawing/floating-point tolerance keeps their centres at least 7 px away.
OBSTACLE_CLEARANCE = 7.0
LANE_SNAP_TOLERANCE = 2.0
# Rechecked video frames show lower moving objects aligned with these central
# exits. Other 15 px stubs remain unchanged rather than inventing connectors.
BOTTOM_RETURN_CONNECTOR_IDS = frozenset({"vertical_5", "vertical_6", "vertical_7", "vertical_8"})
VISUAL_ONLY_COLOR = (172, 187, 196)
GRID_BOUNDS = (226.0, 112.0, 962.0, 648.0)
GRID_CUT_EPSILON = 1.0


@dataclass(frozen=True)
class RectangleObstacle:
    id: str
    left: float
    top: float
    right: float
    bottom: float


@dataclass(frozen=True)
class EndpointGap:
    source_segment: str
    target_segment: str
    source_point: Point
    projected_point: Point
    distance: float


def machine_obstacle(machine: MachineBlock, clearance: float = OBSTACLE_CLEARANCE) -> RectangleObstacle:
    return RectangleObstacle(
        machine.id,
        machine.x - clearance,
        machine.y - clearance,
        machine.x + machine.width + clearance,
        machine.y + machine.height + clearance,
    )


def machine_obstacles(layout: FacilityLayout, clearance: float = OBSTACLE_CLEARANCE) -> tuple[RectangleObstacle, ...]:
    return tuple(machine_obstacle(machine, clearance) for machine in layout.machines)


def station_obstacle(station: Station, clearance: float = OBSTACLE_CLEARANCE) -> RectangleObstacle:
    return RectangleObstacle(
        station.id,
        station.x - clearance,
        station.y - clearance,
        station.x + station.width + clearance,
        station.y + station.height + clearance,
    )


def station_obstacles(layout: FacilityLayout, clearance: float = OBSTACLE_CLEARANCE) -> tuple[RectangleObstacle, ...]:
    return tuple(station_obstacle(station, clearance) for station in layout.stations)


def driving_obstacles(layout: FacilityLayout) -> tuple[RectangleObstacle, ...]:
    return (*machine_obstacles(layout), *station_obstacles(layout))


def point_inside_obstacle(point: Point, obstacle: RectangleObstacle) -> bool:
    return obstacle.left <= point[0] <= obstacle.right and obstacle.top <= point[1] <= obstacle.bottom


def segment_intersects_obstacle(start: Point, end: Point, obstacle: RectangleObstacle) -> bool:
    """Return whether an orthogonal segment touches or enters a closed obstacle."""
    if start[0] != end[0] and start[1] != end[1]:
        raise ValueError("Obstacle validation requires an orthogonal segment")
    if start[0] == end[0]:
        x = start[0]
        low, high = sorted((start[1], end[1]))
        return obstacle.left <= x <= obstacle.right and low <= obstacle.bottom and high >= obstacle.top
    y = start[1]
    low, high = sorted((start[0], end[0]))
    return obstacle.top <= y <= obstacle.bottom and low <= obstacle.right and high >= obstacle.left


def _is_safe_segment(segment: NetworkSegment, obstacles: Iterable[RectangleObstacle]) -> bool:
    return not any(segment_intersects_obstacle(segment.start, segment.end, obstacle) for obstacle in obstacles)


def _relocate_unsafe_verticals(
    segments: tuple[NetworkSegment, ...], obstacles: tuple[RectangleObstacle, ...]
) -> tuple[NetworkSegment, ...]:
    """Move an unsafe reference vertical into the adjacent free aisle.

    The aisle centre is derived from the expanded machine boundary and the
    nearest safe vertical on its right, rather than copied as a second set of
    reference coordinates. Cross aisles retain connectivity between columns.
    """
    safe_vertical_x = sorted({
        segment.start[0]
        for segment in segments
        if segment.start[0] == segment.end[0] and _is_safe_segment(segment, obstacles)
    })
    repaired = []
    for segment in segments:
        if segment.start[0] != segment.end[0] or _is_safe_segment(segment, obstacles):
            repaired.append(segment)
            continue
        crossed = [
            obstacle for obstacle in obstacles
            if segment_intersects_obstacle(segment.start, segment.end, obstacle)
        ]
        right_boundary = max(obstacle.right for obstacle in crossed)
        right_lane = next((x for x in safe_vertical_x if x > right_boundary), None)
        if right_lane is None:
            raise ValueError(f"No safe aisle found for {segment.id}")
        aisle_x = (right_boundary + right_lane) / 2
        candidate = NetworkSegment(
            segment.id, (aisle_x, segment.start[1]), (aisle_x, segment.end[1]),
            segment.color, segment.width, segment.drivable,
        )
        if not _is_safe_segment(candidate, obstacles):
            raise ValueError(f"Derived aisle remains unsafe: {segment.id}")
        repaired.append(candidate)
    return tuple(repaired)


def _connect_observed_bottom_aisles(segments: tuple[NetworkSegment, ...]) -> tuple[NetworkSegment, ...]:
    bottom_y = max(
        segment.start[1]
        for segment in segments
        if segment.start[1] == segment.end[1]
    )
    connected = []
    for segment in segments:
        if segment.id in BOTTOM_RETURN_CONNECTOR_IDS:
            low, high = sorted((segment.start[1], segment.end[1]))
            if low <= bottom_y and high < bottom_y:
                start = segment.start if segment.start[1] == low else segment.end
                end = (start[0], bottom_y)
                connected.append(NetworkSegment(
                    segment.id, start, end, segment.color, segment.width, segment.drivable
                ))
                continue
        connected.append(segment)
    return tuple(connected)


def _separate_unverified_bottom_tails(
    segments: tuple[NetworkSegment, ...],
) -> tuple[tuple[NetworkSegment, ...], tuple[NetworkSegment, ...]]:
    """End unverified driving stubs at a junction and retain their tails as decoration.

    Reference frames show the short vertical tails below the last cross aisle,
    but do not show them joining the bottom return.  Rendering them as grey
    visual-only tails makes the deliberate separation explicit instead of
    presenting a 15 px near-miss between two driving rails.
    """
    horizontal_y = sorted({
        segment.start[1]
        for segment in segments
        if segment.start[1] == segment.end[1]
    })
    junction_y, bottom_y = horizontal_y[-2:]
    driving = []
    tails = []
    for segment in segments:
        vertical = segment.start[0] == segment.end[0]
        low, high = sorted((segment.start[1], segment.end[1])) if vertical else (0, 0)
        if (
            vertical
            and segment.id.startswith("vertical_")
            and segment.id not in BOTTOM_RETURN_CONNECTOR_IDS
            and low < junction_y < high < bottom_y
        ):
            start = segment.start if segment.start[1] == low else segment.end
            driving.append(NetworkSegment(
                segment.id, start, (start[0], junction_y),
                segment.color, segment.width, segment.drivable,
            ))
            tails.append(NetworkSegment(
                f"visual_tail_{segment.id}", (start[0], junction_y), (start[0], high),
                VISUAL_ONLY_COLOR, 0.7, False,
            ))
        else:
            driving.append(segment)
    return tuple(driving), tuple(tails)


def snap_lane_gaps(
    segments: tuple[NetworkSegment, ...], obstacles: tuple[RectangleObstacle, ...]
) -> tuple[NetworkSegment, ...]:
    """Snap only perpendicular endpoint-to-corridor gaps within tolerance."""
    result = []
    for segment in segments:
        points = [segment.start, segment.end]
        vertical = segment.start[0] == segment.end[0]
        for index, point in enumerate(points):
            candidates = []
            for target in segments:
                target_vertical = target.start[0] == target.end[0]
                if target.id == segment.id or target_vertical == vertical:
                    continue
                if target_vertical:
                    low, high = sorted((target.start[1], target.end[1]))
                    projection = (target.start[0], point[1])
                    on_target = low <= point[1] <= high
                else:
                    low, high = sorted((target.start[0], target.end[0]))
                    projection = (point[0], target.start[1])
                    on_target = low <= point[0] <= high
                distance = hypot(projection[0] - point[0], projection[1] - point[1])
                if on_target and 0 < distance <= LANE_SNAP_TOLERANCE:
                    connector = NetworkSegment("snap_check", point, projection)
                    if _is_safe_segment(connector, obstacles):
                        candidates.append((distance, target.id, projection))
            if candidates:
                points[index] = min(candidates)[2]
        result.append(NetworkSegment(
            segment.id, points[0], points[1], segment.color, segment.width, segment.drivable
        ))
    return tuple(result)


def perpendicular_endpoint_gaps(
    segments: Iterable[NetworkSegment], tolerance: float = LANE_SNAP_TOLERANCE
) -> tuple[EndpointGap, ...]:
    """Audit visible near-misses between perpendicular driving segments."""
    segments = tuple(segments)
    gaps = []
    for source in segments:
        source_vertical = source.start[0] == source.end[0]
        for point in (source.start, source.end):
            for target in segments:
                target_vertical = target.start[0] == target.end[0]
                if source.id == target.id or source_vertical == target_vertical:
                    continue
                if target_vertical:
                    low, high = sorted((target.start[1], target.end[1]))
                    projection = (target.start[0], point[1])
                    on_target = low <= point[1] <= high
                else:
                    low, high = sorted((target.start[0], target.end[0]))
                    projection = (point[0], target.start[1])
                    on_target = low <= point[0] <= high
                distance = hypot(projection[0] - point[0], projection[1] - point[1])
                if on_target and 0 < distance <= tolerance:
                    gaps.append(EndpointGap(source.id, target.id, point, projection, distance))
    return tuple(gaps)


def candidate_grid_segments(layout: FacilityLayout) -> tuple[NetworkSegment, ...]:
    """Create a full Manhattan candidate grid from measured aisle coordinates."""
    left, top, right, bottom = GRID_BOUNDS
    vertical_x = sorted({
        segment.start[0]
        for segment in layout.network
        if segment.drivable
        and segment.start[0] == segment.end[0]
        and (segment.id.startswith("vertical_") or segment.id.endswith("loop_a") or segment.id.endswith("loop_c"))
    })
    horizontal_y = sorted({
        segment.start[1]
        for segment in layout.network
        if segment.drivable
        and segment.start[1] == segment.end[1]
        and segment.id.startswith("horizontal_")
    } | {top})
    verticals = tuple(
        NetworkSegment(f"grid_v_{index}", (x, top), (x, bottom), width=0.85)
        for index, x in enumerate(vertical_x)
        if left <= x <= right
    )
    horizontals = tuple(
        NetworkSegment(
            f"grid_h_{index}", (left, y), (right, y),
            width=1.15 if y >= 555 else 0.9,
        )
        for index, y in enumerate(horizontal_y)
        if top <= y <= bottom
    )
    return (*horizontals, *verticals)


def _subtract_blocked_intervals(
    start: float, end: float, blocked: Iterable[tuple[float, float]]
) -> tuple[tuple[float, float], ...]:
    intervals = [(min(start, end), max(start, end))]
    for blocked_start, blocked_end in sorted(blocked):
        cut_start = blocked_start - GRID_CUT_EPSILON
        cut_end = blocked_end + GRID_CUT_EPSILON
        next_intervals = []
        for low, high in intervals:
            if cut_end <= low or cut_start >= high:
                next_intervals.append((low, high))
                continue
            if low < cut_start:
                next_intervals.append((low, min(high, cut_start)))
            if cut_end < high:
                next_intervals.append((max(low, cut_end), high))
        intervals = next_intervals
    return tuple((low, high) for low, high in intervals if high - low > 1e-6)


def prune_grid_segments(
    candidates: Iterable[NetworkSegment], obstacles: Iterable[RectangleObstacle]
) -> tuple[NetworkSegment, ...]:
    """Split candidate centerlines at expanded obstacle rectangles."""
    obstacles = tuple(obstacles)
    surviving = []
    for candidate in candidates:
        vertical = candidate.start[0] == candidate.end[0]
        if vertical:
            x = candidate.start[0]
            blocked = [
                (obstacle.top, obstacle.bottom)
                for obstacle in obstacles
                if obstacle.left <= x <= obstacle.right
            ]
            intervals = _subtract_blocked_intervals(candidate.start[1], candidate.end[1], blocked)
            parts = [((x, low), (x, high)) for low, high in intervals]
        else:
            y = candidate.start[1]
            blocked = [
                (obstacle.left, obstacle.right)
                for obstacle in obstacles
                if obstacle.top <= y <= obstacle.bottom
            ]
            intervals = _subtract_blocked_intervals(candidate.start[0], candidate.end[0], blocked)
            parts = [((low, y), (high, y)) for low, high in intervals]
        surviving.extend(
            NetworkSegment(
                f"{candidate.id}_part_{index}", start, end,
                candidate.color, candidate.width, True,
            )
            for index, (start, end) in enumerate(parts)
        )
    return tuple(surviving)


def obstacle_safe_grid_segments(layout: FacilityLayout) -> tuple[NetworkSegment, ...]:
    return snap_lane_gaps(
        prune_grid_segments(candidate_grid_segments(layout), driving_obstacles(layout)),
        driving_obstacles(layout),
    )


def _reference_lane_segments(
    layout: FacilityLayout,
) -> tuple[tuple[NetworkSegment, ...], tuple[NetworkSegment, ...]]:
    obstacles = machine_obstacles(layout)
    drivable = tuple(segment for segment in layout.network if segment.drivable)
    repaired = _relocate_unsafe_verticals(drivable, obstacles)
    connected = _connect_observed_bottom_aisles(repaired)
    driving, generated_visual = _separate_unverified_bottom_tails(connected)
    return snap_lane_gaps(driving, obstacles), generated_visual


def reference_driving_segments(layout: FacilityLayout) -> tuple[NetworkSegment, ...]:
    return obstacle_safe_grid_segments(layout)


def reference_visual_only_segments(layout: FacilityLayout) -> tuple[NetworkSegment, ...]:
    # top_left/top_right are replaced by the canonical y=112 driving grid rail.
    return tuple(
        segment for segment in layout.network
        if not segment.drivable and segment.id not in {"top_left", "top_right"}
    )


def reference_render_segments(layout: FacilityLayout, graph: LaneGraph) -> tuple[NetworkSegment, ...]:
    """Canonical renderer input: graph edges plus explicitly non-driving detail."""
    return (*graph.network_segments(), *reference_visual_only_segments(layout))


def build_safe_lane_graph(layout: FacilityLayout) -> LaneGraph:
    graph = lane_graph_from_segments(reference_driving_segments(layout))
    validate_lane_graph_safety(graph, driving_obstacles(layout))
    return graph


def unsafe_nodes(graph: LaneGraph, obstacles: Iterable[RectangleObstacle]):
    obstacles = tuple(obstacles)
    return tuple(node for node in graph.nodes if any(point_inside_obstacle(node.position, item) for item in obstacles))


def unsafe_edges(graph: LaneGraph, obstacles: Iterable[RectangleObstacle]):
    obstacles = tuple(obstacles)
    return tuple(
        edge for edge in graph.edges
        if any(segment_intersects_obstacle(graph.node(edge.source).position, graph.node(edge.target).position, item) for item in obstacles)
    )


def validate_lane_graph_safety(graph: LaneGraph, obstacles: Iterable[RectangleObstacle]) -> None:
    obstacles = tuple(obstacles)
    bad_nodes = unsafe_nodes(graph, obstacles)
    bad_edges = unsafe_edges(graph, obstacles)
    if bad_nodes or bad_edges:
        raise ValueError(f"Unsafe lane graph: nodes={len(bad_nodes)} edges={len(bad_edges)}")
