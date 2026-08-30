"""Central node/edge reservations for V4 multi-agent traffic control."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from .lane_graph import LaneEdge
from .motion import LaneMobileEntity


@dataclass(frozen=True)
class ReservationDecision:
    granted: bool
    reason: str = ""


class TrafficController:
    """Owns reservations; it does not plan routes or advance motion."""

    def __init__(self, blocked_warning_seconds: float = 10.0) -> None:
        if blocked_warning_seconds <= 0:
            raise ValueError("blocked warning threshold must be positive")
        self.node_reservations: Dict[str, str] = {}
        self.edge_reservations: Dict[str, str] = {}
        self.conflict_count = 0
        self.waiting_events = 0
        self.blocked_warning_seconds = blocked_warning_seconds
        self.events: list[str] = []
        self._warned_at: Dict[str, float] = {}

    def occupy_node(self, entity_id: str, node_id: str) -> None:
        owner = self.node_reservations.get(node_id)
        if owner is not None and owner != entity_id:
            raise ValueError(f"Node {node_id} is already occupied by {owner}")
        self.node_reservations[node_id] = entity_id

    def request_entry(
        self,
        entity_id: str,
        current_node: str,
        edge: LaneEdge,
        target_node: str,
    ) -> ReservationDecision:
        """Atomically reserve a narrow edge and its destination node."""
        edge_owner = self.edge_reservations.get(edge.id)
        if edge_owner is not None and edge_owner != entity_id:
            self.conflict_count += 1
            return ReservationDecision(False, f"edge {edge.id} reserved by {edge_owner}")
        node_owner = self.node_reservations.get(target_node)
        if node_owner is not None and node_owner != entity_id:
            self.conflict_count += 1
            return ReservationDecision(False, f"node {target_node} reserved by {node_owner}")

        self.edge_reservations[edge.id] = entity_id
        self.node_reservations[target_node] = entity_id
        if self.node_reservations.get(current_node) == entity_id:
            del self.node_reservations[current_node]
        return ReservationDecision(True)

    def complete_edge(self, entity_id: str, edge_id: str, target_node: str) -> None:
        if self.edge_reservations.get(edge_id) != entity_id:
            raise ValueError(f"Entity {entity_id} does not own edge {edge_id}")
        if self.node_reservations.get(target_node) != entity_id:
            raise ValueError(f"Entity {entity_id} does not own target node {target_node}")
        del self.edge_reservations[edge_id]

    def release_entity(self, entity_id: str) -> None:
        self.node_reservations = {
            node: owner for node, owner in self.node_reservations.items() if owner != entity_id
        }
        self.edge_reservations = {
            edge: owner for edge, owner in self.edge_reservations.items() if owner != entity_id
        }

    def note_waiting(self, entity: LaneMobileEntity, delta_time: float, newly_waiting: bool) -> None:
        entity.waiting_count += 1
        entity.waiting_time += delta_time
        if newly_waiting:
            self.waiting_events += 1
        last_warning = self._warned_at.get(entity.id, 0.0)
        if entity.waiting_time >= last_warning + self.blocked_warning_seconds:
            message = f"Traffic warning: {entity.id} blocked for {entity.waiting_time:.1f} seconds"
            self.events.append(message)
            self.events = self.events[-100:]
            self._warned_at[entity.id] = entity.waiting_time

    def clear_waiting(self, entity: LaneMobileEntity) -> None:
        entity.waiting_time = 0.0
        self._warned_at.pop(entity.id, None)

    @staticmethod
    def priority_key(entity: LaneMobileEntity) -> tuple[int, int, str]:
        """Longest wait wins; creation order and ID make ties deterministic."""
        return (-entity.waiting_count, entity.stable_order, entity.id)

    def owner_of_node(self, node_id: str) -> Optional[str]:
        return self.node_reservations.get(node_id)

    def owner_of_edge(self, edge_id: str) -> Optional[str]:
        return self.edge_reservations.get(edge_id)
