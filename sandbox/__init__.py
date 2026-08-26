# Copyright (c) Ultrone Contributors. All rights reserved.
"""General Intelligence Research Sandbox (Sprint D).

A controlled simulation environment for measuring *general* capability --
not specialized military performance. Every capability here is evaluated
entirely inside the sandbox; the simulator is the terminal executor and the
only legal effect of any action is an audited Outcome record
(**Sandbox Terminality invariant**, structurally tested in
``tests/test_sandbox_eval.py``).

Capabilities:

- ``prediction``   -- calibrated belief maintenance under incomplete,
                     shifting observations (the general-world prediction
                     benchmark: calibration, recovery from surprise,
                     graceful degradation on novel regimes).
- ``memory``       -- long-horizon episodic memory and goal management.
- ``planning``     -- domain-general means-ends decomposition over typed
                     skills (transfer across unrelated domains).
- ``tooluse``      -- autonomous composition of registered tools.
- ``world_model``  -- learned transition model + counterfactual queries.
- ``critique``     -- self-critique / error detection over own predictions.
- ``multiagent``   -- noncombat cooperative task allocation.
- ``evaluate``     -- one reproducible capability report card, persisted
                     through the existing tamper-evident audit store.

Design rules: pure Python, deterministic under (seed, configuration),
no external ML dependencies, and reuse -- never reimplementation -- of the
canonical ``DecisionTrace`` / lifecycle / audit foundations.
"""

from sandbox.evaluate import SANDBOX_EVAL_VERSION, CapabilityReport, run_capability_suite
from sandbox.prediction import (
    BayesianBeliefAgent,
    HypothesisWorld,
    PredictionBenchmark,
    UniformAgent,
    summarize,
)

__all__ = [
    "SANDBOX_EVAL_VERSION",
    "CapabilityReport",
    "run_capability_suite",
    "HypothesisWorld",
    "BayesianBeliefAgent",
    "UniformAgent",
    "PredictionBenchmark",
    "summarize",
]
