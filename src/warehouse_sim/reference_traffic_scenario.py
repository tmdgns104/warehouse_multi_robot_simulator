"""Deterministic 16-entity V4 traffic demo on the reference lane graph."""

from __future__ import annotations

import random
from dataclasses import dataclass
from math import hypot

from .facility_layout import EntityShape, FacilityLayout
from .graph_planner import graph_astar
from .lane_graph import LaneGraph, lane_graph_from_segments
from .motion import LaneMobileEntity
from .reference_scenario import create_reference_layout
from .traffic_simulation import TrafficMotionEngine
from .traffic_planner import TrafficZone

DEFAULT_ENTITY_COUNT = 16
MAX_ENTITY_COUNT = 64


@dataclass(frozen=True)
class ReferenceTrafficScenario:
    layout: FacilityLayout
    graph: LaneGraph
    engine: TrafficMotionEngine


def create_reference_traffic_scenario(
    entity_count: int = DEFAULT_ENTITY_COUNT,
    *,
    seed: int = 1234,
    looping: bool = True,
) -> ReferenceTrafficScenario:
    if entity_count <= 0:
        raise ValueError("entity_count must be positive")
    if entity_count > MAX_ENTITY_COUNT:
        raise ValueError(f"entity_count cannot exceed {MAX_ENTITY_COUNT}")

    layout = create_reference_layout()
    graph = lane_graph_from_segments(layout.network)
    randomizer = random.Random(seed)
    candidates = [
        node
        for node in graph.nodes
        if len(graph.neighbors(node.id)) >= 2
        and 226 <= node.x <= 963
        and 112 <= node.y <= 648
    ]
    candidates.sort(key=lambda node: node.id)
    if entity_count > len(candidates):
        raise ValueError("Not enough distinct start nodes")
    starts = randomizer.sample(candidates, entity_count)

    colors = (
        (58, 150, 26),
        (45, 131, 211),
        (185, 143, 46),
        (46, 46, 48),
        (48, 177, 63),
        (51, 161, 201),
    )
    shapes = (EntityShape.RECTANGLE, EntityShape.RECTANGLE, EntityShape.DIAMOND, EntityShape.CIRCLE)
    used_goals = set()
    entities = []
    for index, start in enumerate(starts):
        possible_goals = [
            node
            for node in candidates
            if node.id != start.id
            and node.id not in used_goals
            and hypot(node.x - start.x, node.y - start.y) >= 220
        ]
        randomizer.shuffle(possible_goals)
        goal = next(
            (node for node in possible_goals if graph_astar(graph, start.id, node.id) is not None),
            None,
        )
        if goal is None:
            goal = next(
                node for node in candidates
                if node.id != start.id and graph_astar(graph, start.id, node.id) is not None
            )
        used_goals.add(goal.id)
        shape = shapes[index % len(shapes)]
        size = 9.0 if shape == EntityShape.CIRCLE else 11.0
        entities.append(
            LaneMobileEntity(
                id=f"M{index + 1:02d}",
                current_node=start.id,
                goal_node=goal.id,
                speed=32.0 + (index % 6) * 2.5,
                color=colors[index % len(colors)],
                shape=shape,
                width=size,
                height=size,
            )
        )

    engine = TrafficMotionEngine(
        graph,
        entities,
        seed=seed,
        looping=looping,
        goal_candidates=(node.id for node in candidates),
        blocked_warning_seconds=3.0,
        zones=(
            TrafficZone("upper", frozenset(node.id for node in candidates if node.y < 311), 6),
            TrafficZone("middle", frozenset(node.id for node in candidates if 311 <= node.y < 555), 8),
            TrafficZone("lower", frozenset(node.id for node in candidates if node.y >= 555), 6),
        ),
    )
    return ReferenceTrafficScenario(layout, graph, engine)
