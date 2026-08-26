# Copyright (c) Ultrone Contributors. All rights reserved.
"""Reference implementations of the runtime kernels (pure Python).

These mirror the Rust classes in ``rust/ultrone_core/src`` exactly --
same constructor arguments, same method names, same deterministic
results -- so the loader can swap backends transparently and parity
tests can pin both sides.
"""

from __future__ import annotations

import heapq
import math
from collections import defaultdict
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple


# --------------------------------------------------------------------- #
# World state                                                            #
# --------------------------------------------------------------------- #
class WorldState:
    """Entity store: id -> kinematic state + kind, with fixed-step integration."""

    def __init__(self) -> None:
        self._entities: Dict[str, Dict[str, Any]] = {}
        self._tick = 0

    def spawn(self, entity_id: str, x: float, y: float,
              vx: float = 0.0, vy: float = 0.0,
              kind: str = "unit") -> None:
        if entity_id in self._entities:
            raise ValueError(f"entity '{entity_id}' already exists")
        self._entities[entity_id] = {"x": float(x), "y": float(y),
                                     "vx": float(vx), "vy": float(vy),
                                     "kind": kind}

    def update_velocity(self, entity_id: str,
                        vx: float, vy: float) -> bool:
        entity = self._entities.get(entity_id)
        if entity is None:
            return False
        entity["vx"], entity["vy"] = float(vx), float(vy)
        return True

    def get(self, entity_id: str) -> Optional[Dict[str, Any]]:
        entity = self._entities.get(entity_id)
        return dict(entity) if entity else None

    def step(self, dt: float = 1.0) -> int:
        """Integrate one fixed tick; returns the new tick counter."""
        self._tick += 1
        for entity in self._entities.values():
            entity["x"] += entity["vx"] * dt
            entity["y"] += entity["vy"] * dt
        return self._tick

    def count(self) -> int:
        return len(self._entities)

    def tick(self) -> int:
        return self._tick

    def snapshot(self) -> Dict[str, Any]:
        return {"tick": self._tick,
                "entities": {eid: dict(e)
                             for eid, e in sorted(self._entities.items())}}

    def restore(self, state: Dict[str, Any]) -> None:
        self._tick = int(state["tick"])
        self._entities = {eid: dict(e) for eid, e
                          in state["entities"].items()}


class Simulator:
    """Fixed-step driver over a :class:`WorldState`."""

    def __init__(self, world: WorldState, dt: float = 1.0) -> None:
        self.world = world
        self.dt = float(dt)

    def run(self, ticks: int) -> int:
        for _ in range(int(ticks)):
            self.world.step(self.dt)
        return self.world.tick()


# --------------------------------------------------------------------- #
# Spatial index (uniform grid)                                           #
# --------------------------------------------------------------------- #
class SpatialIndex:
    """Uniform-grid radius queries over static points."""

    def __init__(self, cell_size: float = 1.0) -> None:
        self.cell_size = max(1e-9, float(cell_size))
        self._grid: Dict[Tuple[int, int], List[Tuple[str, float, float]]] \
            = defaultdict(list)

    def insert(self, point_id: str, x: float, y: float) -> None:
        cell = (int(math.floor(x / self.cell_size)),
                int(math.floor(y / self.cell_size)))
        self._grid[cell].append((point_id, float(x), float(y)))

    def query_radius(self, x: float, y: float,
                     radius: float) -> List[str]:
        reach = int(math.ceil(radius / self.cell_size))
        cx, cy = int(math.floor(x / self.cell_size)), \
            int(math.floor(y / self.cell_size))
        hits: List[Tuple[float, str]] = []
        r_sq = radius * radius
        for gx in range(cx - reach, cx + reach + 1):
            for gy in range(cy - reach, cy + reach + 1):
                for point_id, px, py in self._grid.get((gx, gy), ()):
                    d_sq = (px - x) ** 2 + (py - y) ** 2
                    if d_sq <= r_sq:
                        hits.append((d_sq, point_id))
        hits.sort()
        return [point_id for _, point_id in hits]

    def __len__(self) -> int:
        return sum(len(cell) for cell in self._grid.values())


# --------------------------------------------------------------------- #
# Tick scheduler                                                         #
# --------------------------------------------------------------------- #
class TickScheduler:
    """Deterministic tick-ordered task queue (min-heap on tick, then id)."""

    def __init__(self) -> None:
        self._heap: List[Tuple[int, str]] = []
        self._payloads: Dict[str, Any] = {}
        self._cancelled: set = set()

    def schedule(self, tick: int, task_id: str,
                 payload: Any = None) -> None:
        if task_id in self._payloads:
            raise ValueError(f"task '{task_id}' already scheduled")
        heapq.heappush(self._heap, (int(tick), task_id))
        self._payloads[task_id] = payload

    def cancel(self, task_id: str) -> bool:
        if task_id not in self._payloads:
            return False
        self._payloads.pop(task_id, None)     # pending count drops too
        self._cancelled.add(task_id)
        return True

    def pop_due(self, now_tick: int) -> List[Tuple[str, Any]]:
        due: List[Tuple[str, Any]] = []
        while self._heap and self._heap[0][0] <= now_tick:
            tick, task_id = heapq.heappop(self._heap)
            if task_id in self._cancelled:
                self._cancelled.discard(task_id)
                self._payloads.pop(task_id, None)
                continue
            due.append((task_id, self._payloads.pop(task_id)))
        return due

    def pending(self) -> int:
        return len(self._payloads)


# --------------------------------------------------------------------- #
# Command routing (validation + audit; execution stays caller-side)      #
# --------------------------------------------------------------------- #
class CommandRouter:
    """Route table + audit log mirroring the Python-side command path."""

    MAX_LOG = 256

    def __init__(self) -> None:
        self._routes: Dict[str, Dict[str, str]] = defaultdict(dict)
        self._log: List[Dict[str, Any]] = []

    def register(self, target: str, action: str,
                 schema: str = "") -> bool:
        if target in self._routes and action in self._routes[target]:
            raise ValueError(
                f"route {target}.{action} already registered")
        self._routes[target][action] = schema
        return True

    def route(self, target: str, action: str,
              payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        known = target in self._routes \
            and action in self._routes.get(target, {})
        entry = {"target": target, "action": action,
                 "accepted": known}
        self._log.append(entry)
        del self._log[:-self.MAX_LOG]
        if not known:
            return {"ok": False,
                    "error": f"unknown route {target}.{action}"}
        return {"ok": True, "schema": self._routes[target][action]}

    def routes_for(self, target: str) -> List[str]:
        return sorted(self._routes.get(target, {}))

    def log_tail(self, n: int = 10) -> List[Dict[str, Any]]:
        return list(self._log[-n:])


# --------------------------------------------------------------------- #
# Memory index (inverted keyword index)                                  #
# --------------------------------------------------------------------- #
class MemoryIndex:
    """Inverted index: token -> document ids, with removal."""

    def __init__(self) -> None:
        self._index: Dict[str, set] = defaultdict(set)
        self._docs: Dict[str, str] = {}

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return [token.strip(".,;:!?)(").lower()
                for token in text.split() if token.strip(".,;:!?)(")]

    def index_document(self, doc_id: str, text: str) -> int:
        if doc_id in self._docs:
            raise ValueError(f"document '{doc_id}' already indexed")
        tokens = self._tokenize(text)
        for token in tokens:
            self._index[token].add(doc_id)
        self._docs[doc_id] = text
        return len(tokens)

    def search(self, term: str) -> List[str]:
        return sorted(self._index.get(term.strip().lower(), ()))

    def remove_document(self, doc_id: str) -> bool:
        text = self._docs.pop(doc_id, None)
        if text is None:
            return False
        for token in self._tokenize(text):
            bucket = self._index.get(token)
            if bucket is not None:
                bucket.discard(doc_id)
                if not bucket:
                    del self._index[token]
        return True

    def stats(self) -> Dict[str, int]:
        return {"documents": len(self._docs), "terms": len(self._index)}


# --------------------------------------------------------------------- #
# Tensor-ish ops + batch evaluation                                      #
# --------------------------------------------------------------------- #
def dot_product(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = dot_product(a, b)
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def softmax(scores: List[float], temperature: float = 1.0) -> List[float]:
    if not scores:
        return []
    temp = max(1e-9, float(temperature))
    peak = max(scores)
    exps = [math.exp((v - peak) / temp) for v in scores]
    total = sum(exps)
    return [v / total for v in exps]


def top_k_indices(scores: List[float], k: int) -> List[int]:
    order = sorted(range(len(scores)),
                   key=lambda i: (-scores[i], i))
    return order[:max(0, int(k))]


def batch_sphere_eval(population: List[List[float]]) -> List[float]:
    """Deterministic benchmark: sum of squares per individual."""
    return [round(sum(x * x for x in individual), 6)
            if individual else 0.0
            for individual in population]