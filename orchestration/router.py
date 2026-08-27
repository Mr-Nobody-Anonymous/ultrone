# Copyright (c) Ultrone Contributors. All rights reserved.
"""RoutingPolicy + Orchestrator: the model/tool/memory decision loop.

This is the seam between *what a task needs* (TaskProfile) and *what
ULTRONE spends on it* (models, tools, memory strategies, skills,
planning parameters). Selection is transparent and threshold-driven;
the thresholds and preference weights are ordinary registry parameters
(``default_routing_registry`` below), which is precisely what makes the
policy evolvable: ``AdaptiveOptimizer`` mutates them exactly as it does
patrol speeds, and every resulting configuration flows through the same
Evaluator / PromotionGate / BrainStore pipeline as any other adaptive
candidate::

              TaskProfile
                  |
          RoutingPolicy.decide()      <- registry knobs
                  v
       ranked RoutingDecisions
                  v
   execute -> Validator --accept--> StructuredResult
                |                      |
             retry/fallback         trace + ExperienceMemory

Selection-time judgments are policy estimates; execution-time truth
comes from :func:`Orchestrator._simulate_quality`, a deterministic
backend-agnostic stand-in with one documented job: reward capability
fit and penalize mismatch so routing quality is *measurable* today and
swappable for live providers tomorrow without touching anything above
this seam.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

from adaptive.optimizer import config_hash
from adaptive.parameter_registry import ParameterRegistry

from brain.learning.experience_memory import (
    EngagementHistory,
    EngagementOutcome,
)

from orchestration.context_builder import ContextBundle, build_context
from orchestration.cost_policy import CostEstimate, CostPolicy, price_items
from orchestration.fallback import FallbackChain, build_chain
from orchestration.memory_router import (
    MemoryRegistry,
    MemoryStrategy,
    default_memory_registry,
    select_memory,
)
from orchestration.model_registry import (
    DIMENSIONS,
    ModelRegistry,
    ModelSpec,
    default_model_registry,
)
from orchestration.result_validator import (
    StructuredResult,
    ValidationReport,
    demand_level,
    validate_result,
)
from orchestration.skill_router import (
    SkillRegistry,
    SkillSpec,
    default_skill_registry,
    select_skills,
)
from orchestration.task_classifier import TaskProfile, classify
from orchestration.tool_registry import (
    ToolRegistry,
    ToolSpec,
    default_tool_registry,
    select_tools,
)


def default_routing_registry() -> ParameterRegistry:
    """Every tunable routing knob, declared once, bounds enforced.

    These are the genes the AdaptiveOptimizer may recombine. Defaults
    are deliberately *mediocre-but-functional*: an untrained policy
    runs, wastes money on easy tasks, occasionally under-provisions
    hard ones -- leaving visible room for evolution to earn its keep.
    """
    registry = ParameterRegistry()

    def declare_float(name, default, lo, hi, desc):
        registry.declare(name, "float", default, bounds=(lo, hi),
                         metric="orchestration_utility",
                         description=desc)

    def declare_int(name, default, lo, hi, desc):
        registry.declare(name, "int", default, bounds=(lo, hi),
                         metric="orchestration_utility",
                         description=desc)

    declare_float(
        "routing.simple_threshold", 0.35, 0.0, 1.0,
        "tasks at or below this difficulty enter the economy regime")
    declare_float(
        "routing.complexity_threshold", 0.60, 0.0, 1.0,
        "reasoning depth at or above this enters the premium regime")
    declare_float(
        "routing.cost_weight", 0.50, 0.0, 2.0,
        "baseline aversion to spending credits")
    declare_float(
        "routing.latency_weight", 0.40, 0.0, 2.0,
        "baseline aversion to waiting")
    declare_float(
        "routing.memory_weight", 0.30, 0.0, 2.0,
        "appetite for richer memory strategies")
    declare_int(
        "routing.planning_depth", 3, 1, 6,
        "planning depth parameter handed to the executor")
    declare_int(
        "routing.iterations", 3, 1, 8,
        "reasoning iterations handed to the executor")
    declare_int(
        "routing.max_tools", 2, 0, 4,
        "toolkit size ceiling per routed run")
    declare_int(
        "routing.max_skills", 2, 0, 3,
        "skill attach ceiling per routed run")
    declare_float(
        "routing.context_headroom", 0.20, 0.0, 1.0,
        "safety margin multiplied onto estimated token demand")
    declare_float(
        "validate.demand_floor", 0.32, 0.20, 0.50,
        "demand-bar intercept at zero difficulty (slope is contract)")
    declare_float(
        "validate.min_confidence", 0.35, 0.20, 0.90,
        "confidence gate applied by the result validator")
    declare_float(
        "routing.budget_cap_credits", 6.0, 0.5, 12.0,
        "hard per-run credit ceiling enforced between fallback attempts")
    return registry


@dataclass(frozen=True)
class RoutingDecision:
    """One complete resource plan for one task (ranked candidate)."""

    model: ModelSpec
    memory: MemoryStrategy
    tools: Tuple[ToolSpec, ...]
    skills: Tuple[SkillSpec, ...]
    parameters: Dict[str, Any]
    utility: float                     # selection-time estimate
    rationale: str
    estimated: CostEstimate

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model.name,
            "memory": self.memory.name,
            "tools": [t.name for t in self.tools],
            "skills": [s.name for s in self.skills],
            "parameters": dict(self.parameters),
            "utility": self.utility,
            "rationale": self.rationale,
            "estimated_credits": self.estimated.credits,
            "estimated_latency_ms": self.estimated.latency_ms,
        }


def capability_mix(profile: TaskProfile) -> Dict[str, float]:
    """Blend the task's demands into a normalized weight per dimension.

    Shared by selection and by truth simulation so both judge fit on
    the same vocabulary; normalization keeps task families comparable.
    """
    weights = {
        "reasoning": 0.15 + 0.45 * profile.reasoning_depth
                     + 0.20 * profile.difficulty,
        "coding": 0.50 if profile.domain == "coding" else 0.05,
        "retrieval": 0.06 + 0.42 * profile.context_requirement,
        "tool_use": 0.10 + 0.35 * profile.tool_requirement,
    }
    total = sum(weights.values()) or 1.0
    return {d: w / total for d, w in weights.items()}


class RoutingPolicy:
    """Threshold-and-weight routing over a live registry snapshot.

    Three regimes shape willingness to spend:

    - **economy** (difficulty <= simple_threshold): extra cost/latency
      aversion, so trivial tasks land on cheap tiers;
    - **premium** (reasoning_depth >= complexity_threshold): reduced
      price sensitivity plus a reasoning-strength floor -- pay for
      brains when the task actually reasons;
    - **balanced**: defaults.

    Everything the regimes alter is expressed through ordinary weights,
    so an evolved policy can also discover *new* regime boundaries.
    """

    def __init__(self, registry: Optional[ParameterRegistry] = None) -> None:
        self.registry = registry or default_routing_registry()

    # -- parameter reads ------------------------------------------------------ #
    def param(self, name: str) -> Any:
        return self.registry.get(name)

    def _scaled_int(self, name: str, fraction: float) -> int:
        spec = self.registry.spec(name)
        lo, hi = spec.bounds or (0, 1)
        value = lo + (hi - lo) * min(max(fraction, 0.0), 1.0)
        return int(round(value))

    # -- main decision path ----------------------------------------------------- #
    def decide(self, profile: TaskProfile,
               models: Optional[ModelRegistry] = None,
               tools: Optional[ToolRegistry] = None,
               memories: Optional[MemoryRegistry] = None,
               skills: Optional[SkillRegistry] = None,
               max_candidates: int = 3) -> List[RoutingDecision]:
        models = models or default_model_registry()
        tools = tools or default_tool_registry()
        memories = memories or default_memory_registry()
        skills = skills or default_skill_registry()

        need = int(profile.context_tokens
                   * (1.0 + float(self.param("routing.context_headroom"))))

        # Hard filter 1: privacy. Private tasks never leave local tier.
        eligible = [models.get(n) for n in models.names()]
        if profile.privacy_required:
            eligible = [m for m in eligible if m.local_only]

        # Hard filter 2: context window with policy headroom.
        fitting = [m for m in eligible if m.context_window >= need]
        if not fitting:                      # relaxed fallback: smallest
            fitting = sorted(eligible,          # window overflow first
                             key=lambda m: (m.context_window, m.name))
        if not fitting:
            return []

        economy = (profile.difficulty
                   <= float(self.param("routing.simple_threshold")))
        premium = (profile.reasoning_depth >= float(
            self.param("routing.complexity_threshold")))

        eff_cost_w = float(self.param("routing.cost_weight"))
        eff_lat_w = float(self.param("routing.latency_weight"))
        strength_floor = 0.0
        rationale_tag = "[balanced]"
        if economy:
            eff_cost_w += 0.80
            eff_lat_w += 0.30 * profile.latency_sensitivity
            rationale_tag = "[economy]"
        elif premium:
            eff_cost_w *= 0.55
            eff_lat_w *= 0.70
            strength_floor = 0.50
            rationale_tag = "[complexity]"
        strong = [m for m in fitting
                  if m.strengths["reasoning"] >= strength_floor]
        candidates_pool = strong or fitting

        # Premium regime buys capability, not bargains: local tiers
        # stay eligible only while privacy leaves no alternative.
        if premium and not profile.privacy_required:
            cloud = [m for m in candidates_pool if not m.local_only]
            candidates_pool = cloud or candidates_pool

        plan_depth = self._scaled_int(
            "routing.planning_depth", profile.reasoning_depth)
        iterations = self._scaled_int(
            "routing.iterations", 0.4 + 0.6 * profile.difficulty)

        memory_choice = select_memory(
            memories, profile,
            richness_weight=float(self.param("routing.memory_weight")))
        tool_kit = select_tools(
            tools, profile, int(self.param("routing.max_tools")))
        skill_set = select_skills(
            skills, profile, int(self.param("routing.max_skills")))

        shared_price = price_items(
            [(t.cost_per_call, t.latency_ms) for t in tool_kit] +
            [(memory_choice.cost_per_call, memory_choice.latency_ms)] +
            [(s.cost_per_use, s.latency_ms) for s in skill_set])
        cost_policy = CostPolicy(
            cost_weight=eff_cost_w, latency_weight=eff_lat_w)
        mix = capability_mix(profile)

        decisions: List[Tuple[float, str, RoutingDecision]] = []
        for model in candidates_pool:
            attempt_price = cost_policy.estimate(
                CostEstimate(credits=model.cost_per_call,
                             latency_ms=model.latency_ms),
                shared_price)
            cap = sum(mix[d] * model.strengths[d] for d in DIMENSIONS)
            penalty = cost_policy.penalty(
                attempt_price, profile.latency_sensitivity)
            # Capability surplus is waste: an easy task gains nothing
            # from capability it never uses. The economy regime dents
            # oversizing hardest -- without this, premium tiers win
            # even on trivial work purely on raw fit.
            demand_proxy = clamp01(0.35 + 0.45 * profile.difficulty)
            surplus = max(0.0, cap - demand_proxy)
            surplus_rate = 0.20 if economy else 0.05
            utility = round(cap - penalty - surplus_rate * surplus, 6)
            why = (f"{rationale_tag} fit={cap:.3f} "
                   f"penalty={penalty:.3f}")
            if premium and strength_floor:
                why += " reasoning floor enforced"
            decisions.append((utility, model.name, RoutingDecision(
                model=model, memory=memory_choice, tools=tool_kit,
                skills=skill_set,
                parameters={
                    "planning_depth": plan_depth,
                    "iterations": iterations,
                    "context_tokens_needed": profile.context_tokens,
                    "token_budget": model.context_window,
                },
                utility=utility, rationale=why,
                estimated=attempt_price)))

        decisions.sort(key=lambda item: (-item[0], item[1]))
        return [d for _, _, d in decisions[:max_candidates]]


# --------------------------------------------------------------------- #
# Execution truth: deterministic simulated backends                      #
# --------------------------------------------------------------------- #
#: Truth constants. The judge may know these; the ROUTING POLICY does
#: not read them -- it only sees ModelSpec-level declarations. That
#: separation is what makes selection quality measurable rather than
#: self-fulfilling.
_BASE_FLOOR = 0.15
_CAP_GAIN = 0.65                 # strongest possible pure fit ~= 0.80
_DEPTH_GAIN = 0.035
_DEPTH_NEED_FACTOR = 4           # depth needed ~= 4 * reasoning_depth
_DEPTH_OVERSHOOT_COST = 0.02     # wasted planning depth per unit
_ITER_GAIN = 0.02
_ITER_NEED_BASE = 1              # iterations needed ~= 1 + 3 * difficulty
_ITER_NEED_FACTOR = 3
_ITER_OVERSHOOT_COST = 0.015
_TOOL_HIT_GAIN = 0.15            # scaled by tool_requirement * match
_TOOL_MISS_PENALTY = 0.30        # demanded tools absent
_MEMORY_SHORTFALL_PENALTY = 0.35
_SKILL_TRANSFER = 0.45           # skill bonus realization factor
_SKILL_REALIZATION_BASE = 0.25   # easy tasks cannot exploit full skill
_TRUNCATION_PENALTY = 0.06       # silently-lost context is a real loss
_RETRY_FATIGUE = 0.025           # per prior failed attempt

#: Utility credit saturates this far above the SLO demand bar.
_SLO_SLACK = 0.05


def clamp01(value: float) -> float:
    return min(1.0, max(0.0, float(value)))


def simulate_quality(decision: RoutingDecision, profile: TaskProfile,
                     bundle: ContextBundle,
                     attempt_index: int) -> float:
    """Judge one attempt's true output fidelity (deterministic).

    Composition: capability fit against the task's demand mix, plus
    parameter usefulness with diminishing returns and overshoot waste,
    tool/memory/skill contributions or shortfalls, truncation and
    retry-fatigue penalties -- all clamped into [0, 1]. Deterministic
    so identical routes on identical tasks score identically forever.
    """
    strengths = decision.model.strengths
    mix = capability_mix(profile)
    cap = sum(mix[d] * strengths[d] for d in DIMENSIONS)

    # Weaker executors realize less value from the same toolkit -- a
    # second-order effect that keeps quality discriminative instead of
    # saturating near 1.0 for every candidate. Memory shortfall stays
    # unfactored: under-provisioned recall hurts regardless of who runs.
    fit_gain = 0.35 + 0.65 * cap

    plan = int(decision.parameters.get("planning_depth", 1))
    iterations = int(decision.parameters.get("iterations", 1))
    needed_depth = max(1, int(round(_DEPTH_NEED_FACTOR
                                    * profile.reasoning_depth)))
    needed_iters = (_ITER_NEED_BASE
                    + int(round(_ITER_NEED_FACTOR * profile.difficulty)))

    depth_term = (_DEPTH_GAIN * min(plan, needed_depth)
                  * strengths["reasoning"]
                  - _DEPTH_OVERSHOOT_COST * max(0, plan - needed_depth))
    iter_term = (_ITER_GAIN * min(iterations, needed_iters)
                 * strengths["reasoning"]
                 - _ITER_OVERSHOOT_COST * max(0, iterations - needed_iters))

    if profile.tool_requirement > 0.0:
        if decision.tools:
            match = sum(t.reliability for t in decision.tools) \
                / len(decision.tools)
            tool_term = _TOOL_HIT_GAIN * profile.tool_requirement * match
        else:
            tool_term = -_TOOL_MISS_PENALTY * profile.tool_requirement
    else:
        tool_term = 0.0

    memory_support = decision.memory.recall_boost * min(
        1.0, profile.context_requirement
        / max(decision.memory.coverage_until, 0.05))
    shortfall = max(0.0, profile.context_requirement
                    - decision.memory.coverage_until)
    memory_term = memory_support \
        - _MEMORY_SHORTFALL_PENALTY * shortfall

    skill_realization = clamp01(_SKILL_REALIZATION_BASE
                                + profile.difficulty)
    skill_term = _SKILL_TRANSFER * sum(s.bonus for s in decision.skills) \
        * skill_realization

    # fit_gain applies to productive bonuses only; overshoot and
    # shortfall costs are absolute.
    depth_term *= fit_gain
    iter_gain_part = _ITER_GAIN * min(iterations, needed_iters) \
        * strengths["reasoning"]
    iter_cost_part = _ITER_OVERSHOOT_COST * max(0,
                                                iterations - needed_iters)
    iter_term = iter_gain_part * fit_gain - iter_cost_part
    if tool_term > 0:
        tool_term *= fit_gain
    skill_term *= fit_gain

    penalty_total = ((-_TRUNCATION_PENALTY) if bundle.truncated else 0.0)
    fatigue = -_RETRY_FATIGUE * max(0, attempt_index)

    quality = (_BASE_FLOOR + _CAP_GAIN * cap + depth_term + iter_term
               + tool_term + memory_term + skill_term
               + penalty_total + fatigue)
    return round(clamp01(quality), 6)


@dataclass(frozen=True)
class OrchestrationOutcome:
    """Result of one orchestrated task execution."""

    task_id: str
    accepted: bool
    attempts_used: int
    result: Optional[StructuredResult]
    total_cost: float
    total_latency_ms: float
    score: float                    # benchmark utility (see run())
    selected_model: str
    selected_memory: str
    selected_skills: Tuple[str, ...]
    failures: Tuple[str, ...]       # rejection reasons, in order


class Orchestrator:
    """Runs the full routing loop for one task at a time.

    Dependencies are injected registries + a RoutingPolicy over a live
    ParameterRegistry; ``configuration_hash`` stamps every trace with
    the policy snapshot that produced it, keeping traces joinable to
    BrainStore promotions.
    """

    def __init__(self, policy: RoutingPolicy, *,
                 models: Optional[ModelRegistry] = None,
                 tools: Optional[ToolRegistry] = None,
                 memories: Optional[MemoryRegistry] = None,
                 skills: Optional[SkillRegistry] = None,
                 max_attempts: int = 3,
                 executor: Optional[Any] = None) -> None:
        self.policy = policy
        self.models = models or default_model_registry()
        self.tools = tools or default_tool_registry()
        self.memories = memories or default_memory_registry()
        self.skills = skills or default_skill_registry()
        self.max_attempts = int(max_attempts)
        # Execution-truth seam: when provided, called with
        # (decision, profile, bundle, attempt_index) INSTEAD of the
        # built-in simulator. This is where a real ModelAdapter
        # (see self_improvement.self_training.adapters) plugs in --
        # nothing above this seam changes when simulation becomes
        # live inference.
        self.executor = executor

    @property
    def configuration_hash(self) -> str:
        return config_hash(self.policy.registry.snapshot())

    # -- single task --------------------------------------------------------- #
    def run(self,
            task: Union[TaskProfile, Mapping[str, Any]],
            experience: Optional[Any] = None,
            trace_log: Optional[Any] = None) -> OrchestrationOutcome:
        profile = task if isinstance(task, TaskProfile) else classify(task)
        config_hash_at_start = self.configuration_hash

        candidates = self.policy.decide(
            profile, models=self.models, tools=self.tools,
            memories=self.memories, skills=self.skills)
        chain: FallbackChain = build_chain(
            [(-d.utility, d) for d in candidates],
            max_attempts=self.max_attempts)

        cost_policy = CostPolicy(
            cost_weight=float(self.policy.param("routing.cost_weight")),
            latency_weight=float(self.policy.param(
                "routing.latency_weight")),
            budget_cap_credits=float(self.policy.param(
                "routing.budget_cap_credits")))
        failures: List[str] = []
        accepted_result: Optional[StructuredResult] = None
        total_cost = 0.0
        total_latency = 0.0
        attempt_index = 0
        last_decision: Optional[RoutingDecision] = None
        demand_floor = float(self.policy.param("validate.demand_floor"))
        min_confidence = float(self.policy.param("validate.min_confidence"))

        while not accepted_result and not chain.exhausted \
                and attempt_index < self.max_attempts:
            decision = chain.next_candidate()
            if decision is None:
                break
            last_decision = decision

            if not cost_policy.within_budget(CostEstimate(
                    credits=total_cost + decision.estimated.credits,
                    latency_ms=total_latency)):
                failures.append(
                    f"budget exhausted before attempt "
                    f"{attempt_index + 1} ({total_cost:.2f} credits)")
                break

            bundle = build_context(profile, decision.memory,
                                   token_budget=decision.model.context_window)
            judge = self.executor if self.executor is not None \
                else simulate_quality
            quality = judge(decision, profile, bundle, attempt_index)
            result = StructuredResult(
                answer={"task_id": profile.task_id,
                        "via": decision.model.name},
                quality=quality, model=decision.model.name,
                latency_ms=float(decision.estimated.latency_ms),
                artifacts=tuple(t.name for t in decision.tools))
            report: ValidationReport = validate_result(
                result, profile, demand_floor=demand_floor,
                min_confidence=min_confidence)

            total_cost += decision.estimated.credits
            total_latency += decision.estimated.latency_ms
            attempt_index += 1
            if report.ok:
                accepted_result = result
            else:
                failures.append(report.reason)
                chain.record_failure()

        return self._finalize(profile, candidates, last_decision,
                              accepted_result, failures,
                              total_cost, total_latency,
                              attempt_index, config_hash_at_start,
                              experience, trace_log)

    # -- outcome assembly ------------------------------------------------------ #
    def _finalize(self, profile, candidates, last_decision,
                  accepted_result, failures, total_cost, total_latency,
                  attempt_index, config_hash_at_start,
                  experience, trace_log) -> OrchestrationOutcome:
        utility_score = -1.0
        if accepted_result is not None:
            q = accepted_result.quality
            # SLO-based scoring: delivered credit saturates just above
            # the demand bar -- exceeding it buys reputation, not
            # utility -- while every credit and millisecond spent still
            # bills in full. That asymmetry is exactly what teaches the
            # optimizer to stop over-provisioning easy tasks.
            intercept = float(self.policy.param("validate.demand_floor"))
            demand = demand_level(profile, intercept=intercept)
            effective_q = min(q, demand + _SLO_SLACK)
            utility_score = round(
                10.0 * effective_q
                - 0.05 * total_cost
                - 0.002 * total_latency * (0.5 + profile.latency_sensitivity),
                6)

        outcome = OrchestrationOutcome(
            task_id=profile.task_id,
            accepted=accepted_result is not None,
            attempts_used=max(attempt_index, 1),
            result=accepted_result,
            total_cost=round(total_cost, 6),
            total_latency_ms=float(total_latency),
            score=utility_score,
            selected_model=(last_decision.model.name
                            if last_decision else "unrouted"),
            selected_memory=(last_decision.memory.name
                             if last_decision else "unrouted"),
            selected_skills=(tuple(s.name for s in last_decision.skills)
                             if last_decision else ()),
            failures=tuple(failures))

        if experience is not None:
            experience.record_engagement(EngagementHistory(
                engagement_id=f"task::{profile.task_id}",
                attacker_id="orchestrator",
                target_id=profile.domain,
                domain="land",
                engagement_type="routed_task",
                outcome=(EngagementOutcome.SUCCESSFUL if outcome.accepted
                         else EngagementOutcome.PARTIAL),
                duration_ms=outcome.total_latency_ms,
                kill_chain_phases=["route", "execute", "validate"],
                tactics_used=[outcome.selected_model,
                              outcome.selected_memory],
                casualties=0,
                damage_dealt=max(outcome.score, 0.0),
                notes="; ".join(failures[-1:]) or "accepted",
            ))

        if trace_log is not None:
            trace_log.append(OrchestrationTrace(
                task_id=profile.task_id,
                task_profile=profile,
                selected_model=outcome.selected_model,
                selected_memory=outcome.selected_memory,
                selected_skills=outcome.selected_skills,
                parameters=dict(last_decision.parameters)
                if last_decision else {},
                result=(dict(accepted_result.__dict__)
                        if accepted_result else None),
                latency_ms=outcome.total_latency_ms,
                score=outcome.score,
                total_cost=outcome.total_cost,
                failures=[
                    AttemptRecord(
                        attempt=i + 1,
                        model=candidates[min(i, len(candidates)
                                             - 1)].model.name
                        if candidates else "unrouted",
                        memory=candidates[0].memory.name
                        if candidates else "unrouted",
                        tools=(), skills=(), quality=0.0,
                        validated=False, reason=reason, cost=0.0,
                        latency_ms=0.0)
                    for i, reason in enumerate(failures)],
                accepted=outcome.accepted,
                attempts_used=outcome.attempts_used,
                configuration_hash=config_hash_at_start))
        return outcome

    # -- batch helper ---------------------------------------------------------- #
    def run_many(self, tasks: Sequence[Union[TaskProfile,
                                             Mapping[str, Any]]],
                 **kwargs) -> List[OrchestrationOutcome]:
        return [self.run(task, **kwargs) for task in tasks]


# Late binding to avoid import cycles (traces -> task_classifier only).
from orchestration.traces import AttemptRecord, OrchestrationTrace  # noqa: E402