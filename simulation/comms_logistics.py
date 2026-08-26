# Copyright (c) Ultrone Contributors. All rights reserved.
"""Command & communication network + resource/logistics system.

- ``CommunicationNetwork``: clearance levels, priority messages,
  deterministic latency and packet loss. Delivery is deferred to
  ``deliver_due(tick)`` -- the network is part of the simulated world.

- ``LogisticsSystem``: fuel/energy/spares depots; resupply requires the
  machine to be within range of a depot; maintenance clears tool wear.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


CLEARANCE_PUBLIC = 0
CLEARANCE_OPERATOR = 1


@dataclass(frozen=True)
class PendingMessage:
    msg_id: int
    sender: str
    recipient: str
    content: Dict[str, Any]
    deliver_at_tick: int


class CommunicationNetwork:
    def __init__(self, seed: int = 0, base_latency: int = 1,
                 loss_probability: float = 0.05) -> None:
        self.rng = random.Random(seed)
        self.base_latency = base_latency
        self.loss_probability = loss_probability
        self._nodes: Dict[str, int] = {}
        self._pending: List[PendingMessage] = []
        self.inboxes: Dict[str, List[Dict[str, Any]]] = {}
        self._next_id = 0
        self.lost_count = 0

    def register_node(self, node_id: str,
                      clearance: int = CLEARANCE_OPERATOR) -> None:
        self._nodes[node_id] = clearance
        self.inboxes.setdefault(node_id, [])

    def send(self, sender: str, recipient: str, content: Dict[str, Any],
             tick: int, priority: str = "routine",
             required_clearance: int = CLEARANCE_PUBLIC) -> Optional[int]:
        if sender not in self._nodes or recipient not in self._nodes:
            return None
        if self._nodes.get(sender, 0) < required_clearance:
            return None                        # permission denied
        if self.rng.random() < self.loss_probability:
            self.lost_count += 1
            return None                        # packet lost in transit
        latency = max(0, self.base_latency
                      - (2 if priority == "immediate" else 0))
        self._next_id += 1
        pending = PendingMessage(self._next_id, sender, recipient,
                                 dict(content), tick + latency)
        self._pending.append(pending)
        return pending.msg_id

    def deliver_due(self, tick: int) -> int:
        delivered = [m for m in self._pending if m.deliver_at_tick <= tick]
        self._pending = [m for m in self._pending
                         if m.deliver_at_tick > tick]
        for m in delivered:
            inbox = self.inboxes.setdefault(m.recipient, [])
            inbox.append({"msg_id": m.msg_id, "sender": m.sender,
                          "content": m.content})
        return len(delivered)

    @property
    def in_flight(self) -> int:
        return len(self._pending)


# --------------------------------------------------------------------- #
# Resources & logistics                                                  #
# --------------------------------------------------------------------- #
@dataclass
class Depot:
    depot_id: str
    x: float
    y: float
    range_: float = 5.0
    stock: Dict[str, float] = field(default_factory=lambda: {
        "fuel": 500.0, "energy": 1000.0, "spares": 20.0})


class LogisticsSystem:
    """Depots + proximity-based resupply + maintenance clearing."""

    def __init__(self) -> None:
        self.depots: Dict[str, Depot] = {}

    def register_depot(self, depot: Depot) -> None:
        self.depots[depot.depot_id] = depot

    def nearest_depot(self, x: float, y: float) -> Optional[Tuple[str, float]]:
        best: Optional[Tuple[str, float]] = None
        for did, d in sorted(self.depots.items()):
            dist = ((d.x - x) ** 2 + (d.y - y) ** 2) ** 0.5
            if best is None or dist < best[1]:
                best = (did, round(dist, 3))
        return best

    def request_resupply(self, machine, needs: Dict[str, float]
                         ) -> Dict[str, Any]:
        pos = _machine_position(machine)
        if pos is None:
            return {"success": False, "reason": "machine has no position"}
        pick = self.nearest_depot(*pos)
        if pick is None:
            return {"success": False, "reason": "no depot registered"}
        depot_id, dist = pick
        depot = self.depots[depot_id]
        if dist > depot.range_:
            return {"success": False, "in_range": False,
                    "nearest_depot": depot_id, "distance": dist}

        granted: Dict[str, Any] = {}
        fuel_needed = float(needs.get("fuel", 0.0))
        if fuel_needed > 0 and hasattr(machine, "fuel"):
            capacity = float(getattr(machine, "FUEL_CAPACITY", 100.0))
            take = min(fuel_needed, depot.stock["fuel"])
            machine.fuel = min(capacity, machine.fuel + take)
            depot.stock["fuel"] -= take
            granted["fuel"] = round(take, 3)
        energy_needed = float(needs.get("energy", 0.0))
        if energy_needed > 0 and hasattr(machine, "battery_pct"):
            machine.battery_pct = min(100.0, machine.battery_pct
                                      + energy_needed)
            depot.stock["energy"] = max(0.0, depot.stock["energy"]
                                        - energy_needed)
            granted["energy"] = energy_needed
        if needs.get("service") and hasattr(machine, "tool_wear"):
            machine.tool_wear = 0.0
            depot.stock["spares"] = max(0.0, depot.stock["spares"] - 1.0)
            granted["spares"] = 1
        return {"success": True, "depot": depot_id, "granted": granted}


def _machine_position(machine) -> Optional[Tuple[float, float]]:
    if hasattr(machine, "x") and hasattr(machine, "y"):
        return (float(machine.x), float(machine.y))
    if hasattr(machine, "bridge") and hasattr(machine, "trolley"):
        return (float(machine.bridge), float(machine.trolley))
    return None