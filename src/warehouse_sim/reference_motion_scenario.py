"""V3 demo: V2 facility plus a graph and several routed mobile entities."""

from __future__ import annotations

from dataclasses import dataclass

from .facility_layout import EntityShape, FacilityLayout
from .lane_graph import LaneGraph, lane_graph_from_segments
from .motion import LaneMobileEntity, MotionEngine
from .reference_scenario import create_reference_layout


@dataclass(frozen=True)
class ReferenceMotionScenario:
    layout: FacilityLayout
    graph: LaneGraph
    engine: MotionEngine


def create_reference_motion_scenario() -> ReferenceMotionScenario:
    layout = create_reference_layout()
    graph = lane_graph_from_segments(layout.network)

    def node(x, y):
        found = graph.nearest_node((x, y))
        if found.position != (x, y):
            raise ValueError(f"Demo point is not a graph node: {(x, y)}")
        return found.id

    entities = (
        LaneMobileEntity("M1", node(228, 588), node(900, 190), 72, (58, 150, 26)),
        LaneMobileEntity("M2", node(963, 648), node(259, 343), 60, (45, 131, 211), width=14, height=10),
        LaneMobileEntity("M3", node(289, 113), node(870, 618), 54, (46, 46, 48), EntityShape.CIRCLE, 10, 10),
        LaneMobileEntity("M4", node(226, 219), node(962, 433), 66, (185, 143, 46), EntityShape.DIAMOND, 11, 11),
        LaneMobileEntity("M5", node(625, 633), node(289, 190), 58, (48, 177, 63)),
    )
    engine = MotionEngine(graph, entities)
    return ReferenceMotionScenario(layout, graph, engine)
