# Copyright (c) Ultrone Contributors. All rights reserved.
"""Artifact Store — stores and retrieves artifacts (models, checkpoints,
datasets references)."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.MLOps.ArtifactStore")


@dataclass
class Artifact:
    """A stored artifact."""
    artifact_id: str = field(default_factory=lambda: f"a-{uuid.uuid4().hex[:8]}")
    name: str = ""
    artifact_type: str = ""     # model, checkpoint, dataset, report
    version: str = "1.0.0"
    path: str = ""
    size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_id": self.artifact_id, "name": self.name, "artifact_type": self.artifact_type,
            "version": self.version, "path": self.path, "size_bytes": self.size_bytes,
            "metadata": self.metadata, "created_at": self.created_at,
        }


class ArtifactStore:
    """Stores and retrieves artifacts."""

    def __init__(self, base_dir: str = "artifacts"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._artifacts: Dict[str, Artifact] = {}

    def store(self, name: str, artifact_type: str, data: Any = None,
              version: str = "1.0.0", metadata: Optional[Dict[str, Any]] = None) -> Artifact:
        """Store an artifact. If ``data`` is a path, record it; if bytes, write it."""
        artifact = Artifact(name=name, artifact_type=artifact_type, version=version, metadata=metadata or {})
        if isinstance(data, (bytes, bytearray)):
            path = self.base_dir / f"{name}_{artifact.artifact_id}.bin"
            path.write_bytes(bytes(data))
            artifact.path = str(path)
            artifact.size_bytes = len(data)
        elif isinstance(data, str) and Path(data).exists():
            artifact.path = data
            artifact.size_bytes = Path(data).stat().st_size
        else:
            artifact.path = str(self.base_dir / f"{name}_{artifact.artifact_id}")
        self._artifacts[artifact.artifact_id] = artifact
        logger.info("Stored artifact %s (%s)", name, artifact_type)
        return artifact

    def get(self, artifact_id: str) -> Optional[Artifact]:
        return self._artifacts.get(artifact_id)

    def get_by_name(self, name: str) -> List[Artifact]:
        return [a for a in self._artifacts.values() if a.name == name]

    def list_artifacts(self, artifact_type: Optional[str] = None) -> List[Artifact]:
        if artifact_type:
            return [a for a in self._artifacts.values() if a.artifact_type == artifact_type]
        return list(self._artifacts.values())

    def get_stats(self) -> Dict[str, Any]:
        types: Dict[str, int] = {}
        for a in self._artifacts.values():
            types[a.artifact_type] = types.get(a.artifact_type, 0) + 1
        return {
            "type": "ArtifactStore",
            "total_artifacts": len(self._artifacts),
            "by_type": types,
            "base_dir": str(self.base_dir),
        }

