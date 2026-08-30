from warehouse_sim.map import CellType, WarehouseMap
from warehouse_sim.planner import astar


def test_straight_path():
    grid = WarehouseMap(5, 3)
    assert astar(grid, (0, 1), (4, 1)) == [
        (0, 1),
        (1, 1),
        (2, 1),
        (3, 1),
        (4, 1),
    ]


def test_path_detours_around_shelf():
    grid = WarehouseMap(5, 3)
    grid.set_cell((2, 1), CellType.SHELF)
    path = astar(grid, (0, 1), (4, 1))
    assert path is not None
    assert (2, 1) not in path
    assert len(path) == 7


def test_unreachable_goal_returns_none():
    grid = WarehouseMap(3, 3)
    grid.set_cells([(1, 0), (1, 1), (1, 2)], CellType.WALL)
    assert astar(grid, (0, 1), (2, 1)) is None


def test_obstacle_and_out_of_bounds_are_not_walkable():
    grid = WarehouseMap(2, 2)
    grid.set_cell((1, 1), CellType.WALL)
    assert grid.is_walkable((0, 0))
    assert not grid.is_walkable((1, 1))
    assert not grid.is_walkable((-1, 0))
