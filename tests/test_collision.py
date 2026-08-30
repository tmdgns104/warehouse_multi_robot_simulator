from warehouse_sim.collision import resolve_moves
from warehouse_sim.robot import Robot


def test_same_cell_uses_wait_count_then_robot_id_priority():
    first = Robot(1, (0, 1), waiting_count=0)
    second = Robot(2, (2, 1), waiting_count=3)
    allowed = resolve_moves([first, second], {1: (1, 1), 2: (1, 1)})
    assert allowed == {2}


def test_same_cell_tie_uses_lower_robot_id():
    robots = [Robot(1, (0, 1)), Robot(2, (2, 1))]
    assert resolve_moves(robots, {1: (1, 1), 2: (1, 1)}) == {1}


def test_head_on_swap_blocks_both_robots():
    robots = [Robot(1, (0, 0)), Robot(2, (1, 0))]
    allowed = resolve_moves(robots, {1: (1, 0), 2: (0, 0)})
    assert allowed == set()


def test_robot_cannot_enter_cell_of_robot_that_stays():
    robots = [Robot(1, (0, 0)), Robot(2, (1, 0))]
    allowed = resolve_moves(robots, {1: (1, 0), 2: (1, 0)})
    assert allowed == set()
