# Sprint B-D — Persistence Evaluation: can `research_db` become the
# long-term backend for experiment metadata?

**Date:** 2026-08-25 · **Scope:** Sprint B-D · **Verdict: YES for experiment
metadata; NO for the decision audit log (keep the JSONL hash-chained store).**

## 1. What was evaluated

| Candidate | Current role | Data shape |
|---|---|---|
| `ultrone_hitl/audit_store.py` (`JSONLAuditStore`) | System of record for decisions | Append-only JSON Lines; every event hash-chained (`prev_hash`/`hash`, SHA-256); replay + verify |
| `research_db/store.py` (`JSONResearchStore`) | Research notes (papers, experiments, benchmarks, plans) | One pretty-printed JSON file per record; automatic version history on rewrite; SQLite backend also present |

## 2. Findings

### 2.1 The JSONL audit store must not be replaced

- **Tamper evidence.** Each audit event carries `prev_hash` and a digest of
  its canonical body; `store.verify()` recomputes the chain and raises
  `TamperDetectedError`. This is what makes REJECTED→EXECUTED rewrites
  detectable. `JSONResearchStore` has *version history*, but any history
  entry is an independent file that can be edited without detection — there
  is no cryptographic linkage.
- **Exactly-once proposals.** `DuplicateDecisionError` enforces one proposal
  per `decision_id`; the HITL state machine reads current state *from this
  log*. Replacing it would mean re-proving Sprint B-A guarantees on a new
  backend for no concrete gain.
- **Append-only writes.** `os.fsync`-flushed appends only; no rewrite path
  exists. `research_db` rewrites whole record files by design.

Concrete reason to replace? None found. Constraint honored.

### 2.2 `research_db` fits experiment metadata well

The new benchmark suite (`benchmarks/canonical/`) produces per-run records
with exactly the fields `research_db.schema.BenchmarkRecord` models:
metrics, baselines, environment (seed / faults / human policy), status.
`JSONResearchStore.save()` gives idempotent-by-id updates plus automatic
version history — appropriate for *metadata*, where later runs legitimately
update a rolling record.

A thin, fully optional adapter now exists:
`benchmarks/canonical/research_sink.py`
(`persist_run_metadata(records, base_dir)` → `BenchmarkRecord`s).
It is additive; nothing else depends on it, and the benchmark CLI runs
without it.

## 3. Recommendation

1. **Keep** `JSONLAuditStore` as the sole system of record for decisions
   (Sprint A semantics unchanged).
2. **Adopt** `research_db` as the long-term catalog for benchmark/experiment
   metadata via `research_sink.persist_run_metadata`.
3. Defer the SQLite backend of `research_db` until query volume actually
   requires it; the JSON backend already provides history and listing.
4. If audit-log size ever becomes a problem, shard the JSONL log by episode
   or rotate per N events with chained genesis — do not move it into a
   mutable-record store.

## 4. Validation

- `tests/test_research_db.py` (existing Phase 1 tests) still pass untouched.
- New tests in `tests/test_canonical_benchmark.py::TestResearchDbSink`
  prove round-trip persistence of benchmark metadata through
  `research_db`.
