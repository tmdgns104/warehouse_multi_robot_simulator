"""Grid map primitives and the default warehouse layout."""

from __future__ import annotations

from enum import Enum
from typing import Iterable, Iterator, Tuple

Position = Tuple[int, int]


class CellType(str, Enum):
    FREE = "free"
    WALL = "wall"
    SHELF = "shelf"
    STATION = "station"


class WarehouseMap:
    """A rectangular grid whose coordinates are ``(column, row)``."""

    def __init__(self, width: int, height: int) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("Map dimensions must be positive")
        self.width = width
        self.height = height
        self._cells = [
            [CellType.FREE for _ in range(width)] for _ in range(height)
        ]

    def in_bounds(self, position: Position) -> bool:
        x, y = position
        return 0 <= x < self.width and 0 <= y < self.height

    def cell(self, position: Position) -> CellType:
        if not self.in_bounds(position):
            raise IndexError(f"Position outside map: {position}")
        x, y = position
        return self._cells[y][x]

    def set_cell(self, position: Position, cell_type: CellType) -> None:
        if not self.in_bounds(position):
            raise IndexError(f"Position outside map: {position}")
        x, y = position
        self._cells[y][x] = CellType(cell_type)

    def set_cells(self, positions: Iterable[Position], cell_type: CellType) -> None:
        for position in positions:
            self.set_cell(position, cell_type)

    def is_walkable(self, position: Position) -> bool:
        return self.in_bounds(position) and self.cell(position) not in {
            CellType.WALL,
            CellType.SHELF,
        }

    def neighbors(self, position: Position) -> Iterator[Position]:
        x, y = position
        # A stable order makes paths and tests deterministic.
        for candidate in ((x + 1, y), (x, y + 1), (x - 1, y), (x, y - 1)):
            if self.is_walkable(candidate):
                yield candidate


def create_default_warehouse() -> WarehouseMap:
    """Create a warehouse with perimeter walls, shelves, aisles and stations."""
    warehouse = WarehouseMap(22, 16)

    walls = set()
    for x in range(warehouse.width):
        walls.add((x, 0))
        walls.add((x, warehouse.height - 1))
    for y in range(warehouse.height):
        walls.add((0, y))
        walls.add((warehouse.width - 1, y))
    warehouse.set_cells(walls, CellType.WALL)

    # Three shelf blocks leave horizontal cross-aisles at rows 5 and 10.
    shelves = set()
    for left in (4, 9, 14):
        for x in (left, left + 1):
            for y in list(range(2, 5)) + list(range(6, 10)) + list(range(11, 14)):
                shelves.add((x, y))
    warehouse.set_cells(shelves, CellType.SHELF)

    stations = {(2, 2), (19, 2), (2, 13), (19, 13), (11, 5), (11, 10)}
    warehouse.set_cells(stations, CellType.STATION)
    return warehouse
