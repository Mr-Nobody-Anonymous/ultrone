# Copyright (c) Ultrone Contributors. All rights reserved.
"""Learnable sandbox world model with counterfactual queries.

A frequency-table transition model: ``(state, action) -> next-state``
counts learned purely from experience inside the simulator. Supports:

- ``predict``      -- distribution over next states;
- ``surprise``     -- 1 - P(observed next state): prediction error signal;
- ``counterfactual``-- compare predicted outcome distributions of two
  alternative actions from the same state (total-variation divergence).

No gradient machinery: small, inspectable, and exactly reproducible --
appropriate for a sandbox where every number must be explainable.
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import DefaultDict, Dict, Hashable, Optional, Tuple

EPS = 1e-9


class TransitionModel:
    def __init__(self) -> None:
        # (state, action) -> {next_state: count}
        self.counts: DefaultDict[Tuple[Hashable, Hashable], DefaultDict[Hashable, int]] \
            = defaultdict(lambda: defaultdict(int))
        self.n_updates = 0

    def update(self, state, action, next_state) -> None:
        self.counts[(state, action)][next_state] += 1
        self.n_updates += 1

    def predict(self, state, action) -> Dict[Hashable, float]:
        """Outcome distribution; uniform over nothing => empty dict."""
        row = self.counts.get((state, action))
        if not row:
            return {}
        total = sum(row.values())
        return {ns: c / total for ns, c in sorted(row.items())}

    def surprise(self, state, action, actual_next) -> float:
        dist = self.predict(state, action)
        if not dist:
            return 1.0  # maximal surprise about the unknown
        return round(1.0 - dist.get(actual_next, 0.0), 6)

    def counterfactual(self, state, action_a, action_b) -> Dict[str, float]:
        """Total-variation divergence between two imagined futures."""
        da = self.predict(state, action_a)
        db = self.predict(state, action_b)
        keys = sorted(set(da) | set(db))
        if not keys:
            return {"divergence": 0.0}
        tv = 0.5 * sum(abs(da.get(k, 0.0) - db.get(k, 0.0)) for k in keys)
        return {
            "divergence": round(tv, 6),
            "predicted_under_a": {k: round(v, 6) for k, v in da.items()},
            "predicted_under_b": {k: round(v, 6) for k, v in db.items()},
        }

    def to_json(self) -> str:
        payload = {
            "|".join(map(str, k)): dict(v) for k, v in sorted(
                self.counts.items(), key=lambda kv: tuple(map(str, kv[0])),
            )
        }
        return json.dumps(payload, sort_keys=True)
