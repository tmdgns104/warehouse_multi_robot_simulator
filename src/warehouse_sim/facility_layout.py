"""Data models for the video-reference facility layout.

Coordinates use the reference video's 1280 x 720 design space.  Rendering
backends scale this design space to the actual window or image size.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Tuple

Point = Tuple[float, float]
Color = Tuple[int, int, int]


class EntityShape(str, Enum):
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    DIAMOND = "diamond"


@dataclass(frozen=True)
class Zone:
    id: str
    name: str
    x: float
    y: float
    width: float
    height: float
    fill: Color
    outline: Color | None = None


@dataclass(frozen=True)
class MachineBlock:
    id: str
    x: float
    y: float
    width: float = 32
    height: float = 62
    family: str = "blue"


@dataclass(frozen=True)
class Station:
    id: str
    x: float
    y: float
    width: float
    height: float
    color: Color
    orientation: str = "horizontal"


@dataclass(frozen=True)
class NetworkSegment:
    id: str
    start: Point
    end: Point
    color: Color = (218, 133, 145)
    width: float = 1.0

    def __post_init__(self) -> None:
        if self.start[0] != self.end[0] and self.start[1] != self.end[1]:
            raise ValueError("V2 network segments must be orthogonal")
        if self.start == self.end:
            raise ValueError("Network segment must have length")


@dataclass(frozen=True)
class MobileEntity:
    id: str
    x: float
    y: float
    width: float
    height: float
    color: Color
    shape: EntityShape = EntityShape.RECTANGLE
    angle: float = 0.0


@dataclass(frozen=True)
class FacilityLayout:
    design_width: int
    design_height: int
    zones: tuple[Zone, ...] = field(default_factory=tuple)
    machines: tuple[MachineBlock, ...] = field(default_factory=tuple)
    stations: tuple[Station, ...] = field(default_factory=tuple)
    network: tuple[NetworkSegment, ...] = field(default_factory=tuple)
    entities: tuple[MobileEntity, ...] = field(default_factory=tuple)

    def validate(self) -> None:
        if self.design_width <= 0 or self.design_height <= 0:
            raise ValueError("Design dimensions must be positive")
        collections: Iterable[tuple] = (
            self.zones,
            self.machines,
            self.stations,
            self.network,
            self.entities,
        )
        all_ids = [item.id for collection in collections for item in collection]
        if len(all_ids) != len(set(all_ids)):
            raise ValueError("Every layout item ID must be unique")
        for item in (*self.zones, *self.machines, *self.stations, *self.entities):
            if item.width <= 0 or item.height <= 0:
                raise ValueError(f"Invalid size for {item.id}")
            if not (0 <= item.x <= self.design_width and 0 <= item.y <= self.design_height):
                raise ValueError(f"Item origin outside design: {item.id}")

    @property
    def aspect_ratio(self) -> float:
        return self.design_width / self.design_height
