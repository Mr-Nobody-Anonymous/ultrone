# Copyright (c) Ultrone Contributors. All rights reserved.
"""Self-critique / error detection over the agent's own predictions.

The critic inspects PredictionRecords (see ``sandbox.prediction``) and
flags three failure shapes:

- WRONG_TOP        -- the argmax belief was incorrect;
- OVERCONFIDENT    -- >80% confidence on a wrong tick (calibration crime);
- STUCK_LOOP       -- the same wrong top-belief held >=3 consecutive ticks.

Critiques are data, not punishment: they are meant to be remembered
(see ``sandbox.memory``) so future episodes avoid repeating the error.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from sandbox.prediction import PredictionRecord

WRONG_TOP = "WRONG_TOP"
OVERCONFIDENT = "OVERCONFIDENT"
STUCK_LOOP = "STUCK_LOOP"


@dataclass(frozen=True)
class Critique:
    subject_id: str
    kind: str
    detail: str
    severity: float


class SelfCritic:
    def __init__(
        self,
        overconfidence_threshold: float = 0.8,
        loop_length: int = 3,
    ) -> None:
        self.overconfidence_threshold = overconfidence_threshold
        self.loop_length = loop_length

    def review_predictions(
        self, records: List[PredictionRecord], subject_id: str = "agent",
    ) -> List[Critique]:
        critiques: List[Critique] = []
        wrong_run_label: Optional[str] = None
        wrong_run_len = 0
        for r in records:
            if r.correct:
                wrong_run_label = None
                wrong_run_len = 0
                continue
            critiques.append(Critique(
                subject_id=subject_id,
                kind=WRONG_TOP,
                detail=f"tick {r.tick}: believed '{r.top_hypothesis}', "
                       f"truth was '{r.true_state}'",
                severity=round(r.confidence, 3),
            ))
            if r.confidence > self.overconfidence_threshold:
                critiques.append(Critique(
                    subject_id=subject_id,
                    kind=OVERCONFIDENT,
                    detail=f"tick {r.tick}: confidence {r.confidence:.2f} "
                           f"while wrong",
                    severity=round(min(1.0, r.confidence), 3),
                ))
            if r.top_hypothesis == wrong_run_label:
                wrong_run_len += 1
            else:
                wrong_run_label = r.top_hypothesis
                wrong_run_len = 1
            if wrong_run_len == self.loop_length:
                critiques.append(Critique(
                    subject_id=subject_id,
                    kind=STUCK_LOOP,
                    detail=f"ticks {r.tick - self.loop_length + 1}-{r.tick}: "
                           f"held wrong belief '{r.top_hypothesis}' "
                           f"{self.loop_length}x despite contrary evidence",
                    severity=0.9,
                ))
        return critiques
