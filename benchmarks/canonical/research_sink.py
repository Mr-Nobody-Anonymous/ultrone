# Copyright (c) Ultrone Contributors. All rights reserved.
"""Optional experiment-metadata sink into ``research_db`` (Sprint B-D).

Evaluation outcome (see ``docs/RESEARCH_DB_EVALUATION.md``):

- The working JSONL audit store stays the system of record for *decisions*:
  its SHA-256 hash chain is tamper-evident in a way ``research_db``'s
  versioned JSON files are not, and decision records are append-only by law,
  not by convention.
- ``research_db`` IS suitable as the long-term catalog of *experiment
  metadata* (benchmark runs, scenario configs, metrics summaries). This
  adapter mirrors one canonical benchmark result into a
  ``research_db.schema.BenchmarkRecord`` without replacing anything.

The import is guarded so the benchmark suite works even if ``research_db``
is unavailable.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Ultrone.Benchmarks.ResearchSink")


def record_to_benchmark_record(record: Dict[str, Any]):
    """Map a canonical benchmark result onto a research_db BenchmarkRecord."""
    from research_db.schema import BenchmarkRecord

    metrics = dict(record.get("metrics") or {})
    return BenchmarkRecord(
        name=f"canonical:{record['scenario_id']}",
        description=str(
            (record.get("config") or {}).get("description")
            or "canonical DecisionPipeline scenario"
        ),
        task_type="decision_pipeline",
        dataset="ultrone-battlefield-sim",
        metrics=metrics,
        baseline_results={
            "fingerprint": record.get("fingerprint", ""),
            "scenario_suite_version": record.get("scenario_suite_version", ""),
        },
        candidate_results={
            "steps": metrics.get("steps", 0),
            "failures": list(record.get("failures") or []),
            "constraint_violations": record.get("constraint_violations", 0),
        },
        environment={
            "seed": (record.get("config") or {}).get("seed"),
            "human_policy": (record.get("config") or {}).get("human_policy"),
            "faults": (record.get("config") or {}).get("faults"),
        },
        status="completed" if not record.get("failures") else "failed",
    )


def persist_run_metadata(
    records: List[Dict[str, Any]],
    base_dir: "Path | str" = "research_db",
) -> List[str]:
    """Persist benchmark-run metadata into research_db; returns record ids.

    Never touches ultrone_hitl's JSONL decision audit store.
    """
    try:
        from research_db.store import JSONResearchStore
    except ImportError:  # pragma: no cover - optional backend
        logger.warning("research_db unavailable; skipping metadata persistence")
        return []

    store = JSONResearchStore(base_dir=str(base_dir))
    ids: List[str] = []
    for record in records:
        bench = record_to_benchmark_record(record)
        saved = store.save("benchmark", bench)
        ids.append(saved.benchmark_id)
    return ids
