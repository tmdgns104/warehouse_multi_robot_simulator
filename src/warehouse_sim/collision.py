"""One-tick reservation policy for basic multi-robot collision avoidance."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, Set

from .map import Position
from .robot import Robot


def _priority(robot: Robot) -> tuple:
    """A lower tuple wins: longest wait first, then lowest robot ID."""
    return (-robot.waiting_count, robot.id)


def resolve_moves(
    robots: Iterable[Robot], proposals: Dict[int, Position]
) -> Set[int]:
    """Return IDs allowed to move without same-cell or head-on collisions.

    ``proposals`` contains each robot's desired cell. A robot proposing its
    current cell is treated as stationary and keeps that reservation.
    """
    robot_by_id = {robot.id: robot for robot in robots}
    allowed = {
        robot_id
        for robot_id, target in proposals.items()
        if target != robot_by_id[robot_id].position
    }

    # Same destination: a robot already occupying/staying in the cell wins.
    by_target = defaultdict(list)
    for robot_id, target in proposals.items():
        by_target[target].append(robot_id)
    for target, contenders in by_target.items():
        if len(contenders) < 2:
            continue
        stayers = [
            robot_id
            for robot_id in contenders
            if robot_by_id[robot_id].position == target
        ]
        winner = (
            stayers[0]
            if stayers
            else min(contenders, key=lambda rid: _priority(robot_by_id[rid]))
        )
        allowed.difference_update(set(contenders) - {winner})

    # A direct position exchange is unsafe for both robots.
    ids = list(proposals)
    for index, first_id in enumerate(ids):
        for second_id in ids[index + 1 :]:
            first = robot_by_id[first_id]
            second = robot_by_id[second_id]
            if (
                proposals[first_id] == second.position
                and proposals[second_id] == first.position
                and first.position != second.position
            ):
                allowed.discard(first_id)
                allowed.discard(second_id)

    # If a move was cancelled, its current cell becomes occupied. Propagate
    # that fact through a chain of following robots until the result is safe.
    changed = True
    while changed:
        changed = False
        occupied = {
            robot.position
            for robot in robot_by_id.values()
            if robot.id not in allowed
        }
        for robot_id in tuple(allowed):
            if proposals[robot_id] in occupied:
                allowed.remove(robot_id)
                changed = True
    return allowed
