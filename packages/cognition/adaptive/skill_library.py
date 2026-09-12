# Copyright (c) Ultrone Contributors. All rights reserved.
"""Skill library: reusable, benchmarked capabilities instead of relearning.

A Skill is a small unit of competence with declared prerequisites,
inputs/outputs, a benchmark score, and a confidence that updates from
real outcomes. Selection is deterministic: best
``confidence * benchmark_score`` among skills whose category matches
and whose prerequisites are all present in the library.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Skill:
    skill_id: str
    name: str
    category: str
    version: int = 1
    benchmark_score: float = 0.0        # 0..1, from the eval suite
    confidence: float = 0.5             # 0..1, updated from outcomes
    prerequisites: tuple = ()
    inputs: tuple = ()
    outputs: tuple = ()
    handler: Optional[Callable] = field(default=None, repr=False,
                                        compare=False)

    @property
    def utility(self) -> float:
        """Selection weight: what the benchmark says times observed trust."""
        return round(self.confidence * max(0.0, self.benchmark_score), 6)


class SkillLibrary:
    """Registry + selector + outcome-driven confidence updates."""

    CONFIDENCE_ALPHA = 0.3              # weight of new evidence

    def __init__(self) -> None:
        self._skills: Dict[str, Skill] = {}
        self._outcomes: Dict[str, List[bool]] = {}

    # -- registration ----------------------------------------------------- #
    def register(self, skill: Skill) -> Skill:
        if skill.skill_id in self._skills:
            raise ValueError(f"skill '{skill.skill_id}' already registered")
        missing = [p for p in skill.prerequisites if p not in self._skills]
        if missing:
            raise ValueError(
                f"skill '{skill.skill_id}' has unregistered prerequisites:"
                f" {missing}")
        if not 0.0 <= skill.benchmark_score <= 1.0 \
                or not 0.0 <= skill.confidence <= 1.0:
            raise ValueError("benchmark_score/confidence must be in [0,1]")
        self._skills[skill.skill_id] = skill
        return skill

    def register_skill(self, skill_id: str, name: str, category: str,
                       benchmark_score: float, confidence: float = 0.5,
                       prerequisites: Optional[List[str]] = None,
                       inputs: Optional[List[str]] = None,
                       outputs: Optional[List[str]] = None,
                       handler: Optional[Callable] = None) -> Skill:
        return self.register(Skill(
            skill_id=skill_id, name=name, category=category,
            benchmark_score=float(benchmark_score),
            confidence=float(confidence),
            prerequisites=tuple(prerequisites or ()),
            inputs=tuple(inputs or ()),
            outputs=tuple(outputs or ()),
            handler=handler))

    # -- selection ----------------------------------------------------------- #
    def select(self, category: str,
               required_inputs: Optional[List[str]] = None) -> Optional[Skill]:
        """Best usable skill for a situation, or None."""
        required = set(required_inputs or ())
        candidates = [
            skill for skill in self._skills.values()
            if skill.category == category
            and required.issubset(set(skill.inputs))
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda s: (-s.utility, s.skill_id))
        return candidates[0]

    def top_skills(self, category: Optional[str] = None,
                   n: int = 5) -> List[Skill]:
        pool = [s for s in self._skills.values()
                if category is None or s.category == category]
        pool.sort(key=lambda s: (-s.utility, s.skill_id))
        return pool[:n]

    # -- outcomes ---------------------------------------------------------------- #
    def record_outcome(self, skill_id: str, success: bool) -> float:
        """Update confidence from real execution evidence."""
        skill = self._skills.get(skill_id)
        if skill is None:
            raise KeyError(f"unknown skill '{skill_id}'")
        evidence = 1.0 if success else 0.0
        alpha = self.CONFIDENCE_ALPHA
        updated = skill.confidence * (1 - alpha) + evidence * alpha
        # Snap toward exact values to avoid floating drift over long runs.
        skill.confidence = round(updated, 6) if not math.isclose(
            updated, round(updated, 6)) else float(round(updated, 6))
        self._outcomes.setdefault(skill_id, []).append(bool(success))
        return skill.confidence

    # -- introspection -------------------------------------------------------------- #
    def get(self, skill_id: str) -> Skill:
        return self._skills[skill_id]

    def known_ids(self) -> List[str]:
        return sorted(self._skills)

    def export(self) -> Dict[str, Any]:
        return {
            skill_id: {
                "category": s.category,
                "version": s.version,
                "benchmark_score": s.benchmark_score,
                "confidence": s.confidence,
                "utility": s.utility,
                "prerequisites": list(s.prerequisites),
                "outcomes": list(self._outcomes.get(skill_id, [])),
            }
            for skill_id, s in sorted(self._skills.items())
        }