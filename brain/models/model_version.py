# Copyright (c) Ultrone Contributors. All rights reserved.
"""Model Version — semantic versioning for AI models."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Tuple

logger = logging.getLogger("Ultrone.Models.Version")


@dataclass
class ModelVersion:
    """Semantic version for a model."""
    major: int = 1
    minor: int = 0
    patch: int = 0
    pre_release: str = ""
    build: str = ""

    def __str__(self) -> str:
        v = f"{self.major}.{self.minor}.{self.patch}"
        if self.pre_release:
            v += f"-{self.pre_release}"
        if self.build:
            v += f"+{self.build}"
        return v

    @classmethod
    def parse(cls, version_str: str) -> "ModelVersion":
        match = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9.]+))?(?:\+([a-zA-Z0-9.]+))?$", version_str)
        if not match:
            return cls()
        return cls(
            major=int(match.group(1)), minor=int(match.group(2)), patch=int(match.group(3)),
            pre_release=match.group(4) or "", build=match.group(5) or "",
        )

    def bump_major(self) -> "ModelVersion":
        return ModelVersion(self.major + 1, 0, 0)

    def bump_minor(self) -> "ModelVersion":
        return ModelVersion(self.major, self.minor + 1, 0)

    def bump_patch(self) -> "ModelVersion":
        return ModelVersion(self.major, self.minor, self.patch + 1)

    def is_compatible_with(self, other: "ModelVersion") -> bool:
        return self.major == other.major

    def __lt__(self, other: "ModelVersion") -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __gt__(self, other: "ModelVersion") -> bool:
        return (self.major, self.minor, self.patch) > (other.major, other.minor, other.patch)

    def __le__(self, other: "ModelVersion") -> bool:
        return self < other or self == other

    def __ge__(self, other: "ModelVersion") -> bool:
        return self > other or self == other

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ModelVersion):
            return False
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)