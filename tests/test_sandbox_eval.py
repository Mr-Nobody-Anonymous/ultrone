# Copyright (c) Ultrone Contributors. All rights reserved.
"""Capability-suite evaluation + structural invariants (Sprint D)."""

import inspect
import pathlib

import pytest

from sandbox.evaluate import (
    SANDBOX_EVAL_VERSION,
    CapabilityReport,
    all_checks_pass,
    persist_report,
    run_capability_suite,
)


@pytest.fixture(scope="module")
def report():
    return run_capability_suite(seed=0)


class TestCapabilitySuite:
    def test_suite_version_pinned(self, report):
        assert report.version == SANDBOX_EVAL_VERSION
        assert SANDBOX_EVAL_VERSION == "sandbox-eval-v2"

    def test_every_capability_section_passes(self, report):
        assert all_checks_pass(report), {
            k: v for k, v in report.sections.items() if not _is_truthy_section(k, v)
        }

    def test_report_covers_all_twelve_capability_areas(self, report):
        expected_sections = {
            # original six
            "prediction",
            "planning_transfer",
            "tool_use",
            "world_model",
            "self_critique_memory",
            "multi_agent_cooperation",
            # Sprint D completion
            "multimodal_perception",
            "continual_learning",
            "distribution_shift",
            "experience_learning",
            "cross_domain_reasoning",
            "general_agent_integration",
        }
        assert set(report.sections) == expected_sections

    def test_fingerprint_reproducible_across_runs(self):
        a = run_capability_suite(seed=42)
        b = run_capability_suite(seed=42)
        assert a.fingerprint == b.fingerprint
        assert a.sections["prediction"]["bayesian"] \
            == b.sections["prediction"]["bayesian"]

    def test_different_seed_different_fingerprint(self):
        assert (
            run_capability_suite(seed=1).fingerprint
            != run_capability_suite(seed=2).fingerprint
        )


class TestTamperEvidentPersistence:
    def test_report_chains_through_existing_audit_store(self, report, tmp_path):
        from ultrone_hitl.audit_store import JSONLAuditStore

        path = tmp_path / "sandbox_evals.jsonl"
        store = JSONLAuditStore(path)
        persist_report(report, store)
        persist_report(run_capability_suite(seed=1), store)
        assert store.verify() is True
        events = [e for e in store.replay() if e["type"] == "eval-report"]
        assert len(events) == 2
        assert events[0]["payload"]["fingerprint"] == report.fingerprint

    def test_tampering_with_a_report_is_detected(self, report, tmp_path):
        from ultrone_hitl.audit_store import JSONLAuditStore, TamperDetectedError

        path = tmp_path / "evals.jsonl"
        store = JSONLAuditStore(path)
        persist_report(report, store)
        lines = path.read_text(encoding="utf-8").splitlines()
        mutated = lines[0].replace(report.fingerprint[:8], "00000000")
        path.write_text("\n".join([mutated] + lines[1:]) + "\n", encoding="utf-8")
        with pytest.raises(TamperDetectedError):
            store.verify()


class TestSandboxTerminalityInvariant:
    """No sandbox module may reach outside the simulator."""

    FORBIDDEN_MARKERS = (
        "battlefield_env",
        "brain.reasoning.evolutionary_coagen",
        "core.pipeline import DecisionPipeline",
        "hitl_bridge",
        "ultrone_os",
    )

    def test_no_military_or_realworld_executor_imports(self):
        root = pathlib.Path(__file__).resolve().parent.parent / "sandbox"
        sources = "\n".join(
            p.read_text(encoding="utf-8") for p in sorted(root.glob("*.py"))
        )
        low = sources.lower()
        for marker in self.FORBIDDEN_MARKERS:
            assert marker.lower() not in low, f"forbidden marker: {marker}"

    def test_only_imports_are_stdlib_and_audit_store(self):
        """Whitelist check on cross-package imports inside sandbox/."""
        allowed_cross_package = {"ultrone_hitl.audit_store"}
        repo_top_levels = {
            "core", "sim", "brain", "benchmarks", "ultrone_hitl",
            "research_db", "game_ai", "frontier",
        }
        root = pathlib.Path(__file__).resolve().parent.parent / "sandbox"
        bad = []
        for p in sorted(root.glob("*.py")):
            for line in p.read_text(encoding="utf-8").splitlines():
                s = line.strip()
                if not s.startswith(("import ", "from ")):
                    continue
                target = s.split()[1].rstrip(",")
                if target.split(".")[0] not in repo_top_levels:
                    continue  # stdlib or third-party
                if target not in allowed_cross_package:
                    bad.append((p.name, s))
        assert bad == [], f"non-whitelisted cross-package imports: {bad}"


def _is_truthy_section(name: str, section) -> bool:
    return True  # detailed checks live in all_checks_pass
