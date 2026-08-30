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
    blocker: Optional[str] = None
    cycle_prevented: bool = False


@dataclass(frozen=True)
class PredictiveReservation:
    owner: str
    resource_id: str
    resource_kind: str
    eta: float
    expires_at: float


class TrafficController:
    """Owns reservations; it does not plan routes or advance motion."""

    def __init__(self, blocked_warning_seconds: float = 10.0) -> None:
        if blocked_warning_seconds <= 0:
            raise ValueError("blocked warning threshold must be positive")
        self.node_reservations: Dict[str, str] = {}
        self.edge_reservations: Dict[str, str] = {}
        self.conflict_count = 0
        self.head_on_conflict_count = 0
        self.deadlock_prevented_count = 0
        self.waiting_events = 0
        self.blocked_warning_seconds = blocked_warning_seconds
        self.events: list[str] = []
        self._warned_at: Dict[str, float] = {}
        self.predictive_reservations: Dict[tuple[str, str], Dict[str, PredictiveReservation]] = {}
        self.wait_for: Dict[str, str] = {}
        self.current_time = 0.0

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
            self.head_on_conflict_count += 1
            return self._deny(entity_id, edge_owner, f"edge {edge.id} reserved by {edge_owner}")
        node_owner = self.node_reservations.get(target_node)
        if node_owner is not None and node_owner != entity_id:
            self.conflict_count += 1
            return self._deny(entity_id, node_owner, f"node {target_node} reserved by {node_owner}")

        self.edge_reservations[edge.id] = entity_id
        self.node_reservations[target_node] = entity_id
        if self.node_reservations.get(current_node) == entity_id:
            del self.node_reservations[current_node]
        self.wait_for.pop(entity_id, None)
        return ReservationDecision(True)

    def _deny(self, entity_id: str, blocker: str, reason: str) -> ReservationDecision:
        cycle = self.would_create_wait_cycle(entity_id, blocker)
        if cycle:
            self.deadlock_prevented_count += 1
        self.wait_for[entity_id] = blocker
        return ReservationDecision(False, reason, blocker, cycle)

    def would_create_wait_cycle(self, waiter: str, owner: str) -> bool:
        current = owner
        visited = {waiter}
        while current in self.wait_for:
            if current in visited:
                return True
            visited.add(current)
            current = self.wait_for[current]
        return current == waiter

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
        self.wait_for.pop(entity_id, None)
        self.remove_predictions(entity_id)

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
        self.wait_for.pop(entity.id, None)

    def refresh_predictions(
        self,
        entity_id: str,
        resources: list[tuple[str, str, float]],
        *,
        ttl: float = 1.0,
    ) -> None:
        self.remove_predictions(entity_id)
        for kind, resource_id, eta in resources:
            key = (kind, resource_id)
            record = PredictiveReservation(
                entity_id, resource_id, kind, eta, self.current_time + ttl
            )
            self.predictive_reservations.setdefault(key, {})[entity_id] = record

    def remove_predictions(self, entity_id: str) -> None:
        for key in tuple(self.predictive_reservations):
            owners = self.predictive_reservations[key]
            owners.pop(entity_id, None)
            if not owners:
                del self.predictive_reservations[key]

    def expire_predictions(self, now: float) -> None:
        self.current_time = now
        for key in tuple(self.predictive_reservations):
            owners = self.predictive_reservations[key]
            for owner in tuple(owners):
                if owners[owner].expires_at < now:
                    del owners[owner]
            if not owners:
                del self.predictive_reservations[key]

    def prediction_penalty(self, kind: str, resource_id: str, entity_id: str) -> float:
        records = self.predictive_reservations.get((kind, resource_id), {})
        return sum(1.0 / (1.0 + record.eta) for owner, record in records.items() if owner != entity_id)

    @staticmethod
    def priority_key(entity: LaneMobileEntity) -> tuple[int, int, str]:
        """Longest wait wins; creation order and ID make ties deterministic."""
        return (-entity.waiting_count, entity.stable_order, entity.id)

    def owner_of_node(self, node_id: str) -> Optional[str]:
        return self.node_reservations.get(node_id)

    def owner_of_edge(self, edge_id: str) -> Optional[str]:
        return self.edge_reservations.get(edge_id)
