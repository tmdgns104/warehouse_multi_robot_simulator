"""Backend-neutral drawing plan shared by pygame and Pillow evidence output."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional, Tuple

from .facility_layout import Color, EntityShape, FacilityLayout, NetworkSegment


class Primitive(str, Enum):
    RECT = "rect"
    LINE = "line"
    CIRCLE = "circle"
    DIAMOND = "diamond"


@dataclass(frozen=True)
class DrawCommand:
    primitive: Primitive
    points: Tuple[float, ...]
    fill: Color
    width: float = 1.0
    outline: Color | None = None


def build_render_plan(
    layout: FacilityLayout,
    network: Optional[Iterable[NetworkSegment]] = None,
    include_entities: bool = True,
) -> tuple[DrawCommand, ...]:
    """Translate semantic layout data into ordered visual primitives."""
    commands = []
    for zone in layout.zones:
        commands.append(DrawCommand(Primitive.RECT, (zone.x, zone.y, zone.width, zone.height), zone.fill, outline=zone.outline))
    for segment in layout.network if network is None else network:
        commands.append(DrawCommand(Primitive.LINE, (*segment.start, *segment.end), segment.color, segment.width))
    for station in layout.stations:
        commands.append(DrawCommand(Primitive.RECT, (station.x, station.y, station.width, station.height), station.color))
        if station.orientation == "horizontal":
            commands.append(DrawCommand(Primitive.LINE, (station.x, station.y + station.height / 2, station.x + station.width, station.y + station.height / 2), (225, 245, 248), 1))
    for machine in layout.machines:
        base = (69, 205, 221) if machine.family == "cyan" else (61, 132, 207)
        commands.extend((
            DrawCommand(Primitive.RECT, (machine.x, machine.y, machine.width, machine.height), (226, 239, 238)),
            DrawCommand(Primitive.RECT, (machine.x + 3, machine.y + 2, machine.width - 8, machine.height - 4), base),
            DrawCommand(Primitive.RECT, (machine.x + machine.width - 8, machine.y + 2, 5, machine.height - 4), (103, 199, 229)),
            DrawCommand(Primitive.LINE, (machine.x + machine.width / 2, machine.y + 1, machine.x + machine.width / 2, machine.y + machine.height - 1), (235, 73, 75), 2.2),
        ))
    for entity in layout.entities if include_entities else ():
        primitive = {
            EntityShape.RECTANGLE: Primitive.RECT,
            EntityShape.CIRCLE: Primitive.CIRCLE,
            EntityShape.DIAMOND: Primitive.DIAMOND,
        }[entity.shape]
        commands.append(DrawCommand(primitive, (entity.x, entity.y, entity.width, entity.height), entity.color, outline=(83, 83, 65) if entity.shape == EntityShape.DIAMOND else None))
    return tuple(commands)
