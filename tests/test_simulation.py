from warehouse_sim.map import WarehouseMap
from warehouse_sim.robot import Robot, RobotState
from warehouse_sim.simulation import Simulation, create_default_simulation


def test_robot_moves_one_cell_per_tick_and_arrives():
    simulation = Simulation(WarehouseMap(4, 1), [Robot(1, (0, 0), (3, 0))])
    simulation.plan_all()
    simulation.tick()
    assert simulation.robot(1).position == (1, 0)
    assert simulation.robot(1).state == RobotState.MOVING
    simulation.tick()
    simulation.tick()
    assert simulation.robot(1).position == (3, 0)
    assert simulation.robot(1).state == RobotState.ARRIVED
    assert simulation.all_arrived


def test_same_cell_conflict_does_not_overlap():
    robots = [Robot(1, (0, 0), (1, 0)), Robot(2, (2, 0), (1, 0))]
    simulation = Simulation(WarehouseMap(3, 1), robots)
    simulation.plan_all()
    simulation.tick()
    assert len({robot.position for robot in robots}) == 2
    assert robots[0].position == (1, 0)
    assert robots[1].state == RobotState.WAITING


def test_head_on_swap_does_not_exchange_positions():
    robots = [Robot(1, (0, 0), (1, 0)), Robot(2, (1, 0), (0, 0))]
    simulation = Simulation(WarehouseMap(2, 1), robots)
    simulation.plan_all()
    simulation.tick()
    assert [robot.position for robot in robots] == [(0, 0), (1, 0)]
    assert all(robot.state == RobotState.WAITING for robot in robots)


def test_reset_restores_initial_state_and_paths():
    simulation = create_default_simulation()
    starts = [robot.position for robot in simulation.robots]
    simulation.tick()
    simulation.start()
    simulation.reset()
    assert simulation.tick_count == 0
    assert not simulation.running
    assert [robot.position for robot in simulation.robots] == starts
    assert all(robot.path for robot in simulation.robots)


def test_default_simulation_has_four_robots_and_valid_paths():
    simulation = create_default_simulation()
    assert len(simulation.robots) == 4
    assert all(robot.path for robot in simulation.robots)
