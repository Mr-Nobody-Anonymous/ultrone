# Contributing to Ultrone

Thanks for your interest in contributing! Ultrone is a simulation-only
research platform, and contributions of all kinds are welcome.

## Ground rules

1. **Simulation only.** Ultrone models battlefield dynamics for research
   purposes. Never wire it to live hardware, real weapon systems, or
   real-world operational data. See `docs/ARCHITECTURE_INVARIANTS.md`.
2. **Safety gates stay independent.** `core/safety_gate.py` must remain
   outside the optimization path. Do not make the safety gate learnable,
   tunable, or bypassable by the systems it supervises.
3. **One canonical execution path.** All decisions flow through
   `core/pipeline.py` (`DecisionPipeline`). Do not add side doors.
4. **HITL audit chain is append-only.** Never rewrite or delete entries in
   the JSONL hash-chained audit store.

## Development setup

```bash
git clone https://github.com/Mr-Nobody-Anonymous/ultrone.git
cd ultrone
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Python **3.10+** is required (CI tests 3.10 / 3.11 / 3.12).

## Running the tests

```bash
python -m pytest tests/ -q
```

The full suite is large; to run a single area:

```bash
python -m pytest tests/test_neural_module.py -q
python -m pytest tests/api -q          # Ultron integration tests
```

## Pull requests

1. Keep changes focused — one logical change per PR.
2. Add or update tests for any behavior change.
3. Ensure `python -m pytest tests/ -q` passes locally.
4. Describe *what* changed and *why* in the PR body, referencing the
   relevant issue when one exists.

## Style

- Python code follows the existing repository style (type hints where the
  surrounding code uses them, dataclasses for value objects).
- Documentation lives in `docs/`; keep claims in sync with the code
  (test counts, file paths, version numbers).

## Reporting issues

Open a GitHub issue with:
- what you expected,
- what actually happened (full traceback for crashes),
- how to reproduce it (minimal script or test).
