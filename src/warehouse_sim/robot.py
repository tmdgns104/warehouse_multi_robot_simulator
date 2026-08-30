"""Robot data model and its small, explicit state machine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from .map import Position


class RobotState(str, Enum):
    IDLE = "IDLE"
    PLANNING = "PLANNING"
    MOVING = "MOVING"
    WAITING = "WAITING"
    ARRIVED = "ARRIVED"


@dataclass
class Robot:
    id: int
    position: Position
    goal: Optional[Position] = None
    path: List[Position] = field(default_factory=list)
    state: RobotState = RobotState.IDLE
    waiting_count: int = 0

    @property
    def next_position(self) -> Position:
        return self.path[0] if self.path else self.position

    def set_goal(self, goal: Position) -> None:
        self.goal = goal
        self.path.clear()
        self.waiting_count = 0
        self.state = RobotState.PLANNING
