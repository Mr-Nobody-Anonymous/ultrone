# Copyright (c) Ultrone Contributors. All rights reserved.
"""Brain orchestrator - central military C2 system with OODA loop."""

import json
import logging
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

from brain.learning import EvolutionLab, EvolutionConfig, AgentEvolver, PatternRecognizer
from brain.perception import (
    SituationalAwareness, TerrainAnalyzer, BattlefieldAnalyzer, Battlefield3DExporter,
)
from brain.learning import ThreatPattern
from brain.reasoning import (
    TacticalEngine, KillChain, CompositeKillChain,
    DomainEngagement, CompositePhase,
    KillChainCapsule, ActiveEvolutionManager,
    EvolutionaryCOAGenerator,
)
from brain.strategy import Doctrine, OperationalPlanner, StrategicPlanner
from config import MilitaryConfig
from config.doctrine_presets import DoctrineType, get_doctrine_preset
from sim import WorldState
from comms import MessageBus
from generative import (
    TacticalSynthesizer, ScenarioGenerator,
    AdversarialEmulator, ReportGenerator,
)
from brain.reasoning.swarm_genomes import CommanderGenome, RedForceGenome, CoevolutionEngine
from sim.battlefield_env import BattlefieldEnv

# Define PROJECT_ROOT for sys.path manipulation
PROJECT_ROOT = Path(__file__).resolve().parent.parent

logger = logging.getLogger("Ultrone.Brain.Orchestrator")

# Ensure project root is on sys.path for top-level
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Default paths
MEMORY_DIR = PROJECT_ROOT / "memory"
BEST_GENOME_PATH = MEMORY_DIR / "best_genome.json"
COMMANDER_LOG_PATH = MEMORY_DIR / "commander_log.txt"


class TelemetryAccumulator:
    """
    Accumulates step-level telemetry across an episode with time-weighted averaging.
    
    Later steps receive higher weight (linear ramp: 1.0 + 0.1*step_idx),
    so that end-game maneuvers matter more than early positioning.
    """

    def __init__(self) -> None:
        self.hits: int = 0
        self.attempts: int = 0
        self.weapons_used: int = 0
        self.weapons_allocated: int = 0
        self.actions_used: set = set()
        self.blue_on_blue: int = 0
        self.collision_count: int = 0
        self.ecm_active_count: int = 0
        self.steps: int = 0
        self.fuel_consumed: float = 0.0
        self.supply_nodes_alive: int = 2
        self.total_supply_nodes: int = 2
        self.supply_penalty_active: bool = False
        self.avg_fuel: float = 1.0
        self._weighted_accuracy: float = 0.0
        self._weight_sum: float = 0.0

    def add_step(self, step_telemetry: Dict[str, Any], step_idx: int) -> None:
        weight = 1.0 + 0.1 * step_idx
        self.steps += 1
        self.hits += step_telemetry.get("hits", 0)
        self.attempts += step_telemetry.get("attempts", 0)
        self.weapons_used += step_telemetry.get("weapons_used", 0)
        self.weapons_allocated += step_telemetry.get("weapons_allocated", 0)
        for a in step_telemetry.get("actions_used", []):
            self.actions_used.add(a)
        self.blue_on_blue += step_telemetry.get("blue_on_blue", 0)
        self.collision_count += step_telemetry.get("collision_count", 0)
        if step_telemetry.get("ecm_active", False):
            self.ecm_active_count += 1
        self.fuel_consumed += step_telemetry.get("fuel_consumed", 0.0)
        step_hit = 1.0 if step_telemetry.get("hits", 0) > 0 else 0.0
        self._weighted_accuracy += weight * step_hit
        self._weight_sum += weight

    def finalize(self, total_steps: int, red_survived: bool) -> Dict[str, Any]:
        self.actions_used.discard(None)
        return {
            "hits": self.hits,
            "attempts": max(1, self.attempts),
            "weapons_used": max(1, self.weapons_used),
            "weapons_allocated": max(1, self.weapons_allocated),
            "actions_used": list(self.actions_used),
            "blue_on_blue": self.blue_on_blue,
            "collision_count": self.collision_count,
            "red_survived": red_survived,
            "ecm_active": self.ecm_active_count > 0,
            "total_steps": total_steps,
            "time_weighted_accuracy": (
                self._weighted_accuracy / self._weight_sum if self._weight_sum > 0 else 0.0
            ),
            "fuel_consumed": self.fuel_consumed,
            "supply_nodes_alive": self.supply_nodes_alive,
            "total_supply_nodes": self.total_supply_nodes,
            "supply_penalty_active": self.supply_penalty_active,
            "avg_fuel": self.avg_fuel,
        }


class Orchestrator:
    """
    Central brain / Command and Control with OODA loop.
    
    Active Evolution:
    - Observe: Perceive threats via sensor fusion
    - Orient: Check for recognized enemy patterns, IMMEDIATELY mutate KillChainCapsule
    - Decide: Generate COAs using evolved parameters
    - Act: Execute updated tactics immediately
    
    The brain physically changes its parameters mid-battle!
    """

    def __init__(
        self,
        config: Optional[MilitaryConfig] = None,
        num_episodes: int = 100,
        max_steps_per_episode: int = 200,
        initial_mutation_rate: float = 0.15,
        use_coevolution: bool = True,
        success_rate_window: int = 10,
        seed: Optional[int] = None,
    ):
        self.config = config or MilitaryConfig()

        self.num_episodes = num_episodes
        self.max_steps_per_episode = max_steps_per_episode
        self.current_mutation_rate = initial_mutation_rate
        self.use_coevolution = use_coevolution
        self.success_rate_window = success_rate_window
        self.seed = seed

        self.episode_rewards: List[float] = []
        self.episode_successes: List[bool] = []
        self.red_survival_rates: List[float] = []
        self.best_genome: Optional[Any] = None
        self.best_fitness: float = 0.0
        self.generation: int = 0

        self.coevolution: Optional[CoevolutionEngine] = None

        self._briefing_generator: Optional[Any] = None
        self._llm_commander: Optional[Any] = None
        self._secretary_council: Optional[Any] = None
        self._current_directive: Optional[Any] = None
        self._analyze_red_behavior: Optional[Any] = None
        self._analyze_blue_attrition: Optional[Any] = None

        self._intervention_manager: Optional[Any] = None
        self._api_server: Optional[Any] = None
        self._hard_blacklist: set = set()
        self._safety_stats = {"proposed": 0, "blocked": 0, "fleet_blocked": 0}

        self.evolution_lab = EvolutionLab()
        self.evolution_lab.initialize(agent_id="orchestrator")

        self.agent_evolver = AgentEvolver(self.evolution_lab)

        self.situational_awareness = SituationalAwareness()

        # Battlefield analysis & 3D imaging
        self.terrain_analyzer = TerrainAnalyzer()
        self.battlefield_analyzer = BattlefieldAnalyzer(self.terrain_analyzer.terrain)
        self.battlefield_3d = Battlefield3DExporter(
            self.terrain_analyzer, self.battlefield_analyzer,
        )
        self.last_analysis: Dict[str, Any] = {}
        self.last_units: Optional[List[Any]] = None
        self.last_contacts: Optional[List[Any]] = None
        self._current_env: Optional[Any] = None

        self.tactical_engine = TacticalEngine()
        self.kill_chain = KillChain()
        self.composite_chains: Dict[str, CompositeKillChain] = {}

        self.active_evolution = ActiveEvolutionManager(
            self.evolution_lab.genome_engine,
            self.kill_chain
        )

        self.pattern_recognizer = PatternRecognizer()

        self.doctrine = Doctrine(get_doctrine_preset(DoctrineType.BALANCED))
        self.operational_planner = OperationalPlanner()
        self.strategic_planner = StrategicPlanner()

        self.message_bus = MessageBus()

        self.tactical_synthesizer = TacticalSynthesizer()
        self.scenario_generator = ScenarioGenerator()
        self.adversarial_emulator = AdversarialEmulator()
        self.report_generator = ReportGenerator()

        self._ooda_cycle = 0
        self._generative_tick = 0
        self._mutations_performed = 0
        self._active_mutations: Dict[str, int] = {}

    async def initialize(self) -> None:
        await self.message_bus.start()
        self.active_evolution.initialize_capsule("orchestrator")
        logger.info("Orchestrator initialized with balanced doctrine and active evolution")

    async def process_tick(self, world_state: WorldState, tick: int) -> Dict[str, Any]:
        self._ooda_cycle += 1
        units = list(world_state.units.values())
        self.situational_awareness.update([], units)
        threatening = self.situational_awareness.get_threatening_contacts()
        detected_patterns = self.orient_phase(threatening, tick)
        assessments = self.tactical_engine.decide(threatening, units)
        results = self.tactical_engine.execute({u.unit_id: u for u in units})
        for assessment in assessments:
            self.evolution_lab.log_action(
                action="tactical_assessment",
                domain="all",
                success=random.random() > 0.2,
                response_time_ms=100.0,
                context={"assessment": assessment.to_dict()},
            )
        return {
            "tick": tick,
            "threats_detected": len(threatening),
            "assessments": len(assessments),
            "orders_executed": results.get("executed", 0),
            "mutations_this_tick": sum(1 for p in detected_patterns if p.confidence > 0.8),
            "active_capabilities": self._get_active_capabilities(),
        }

    def _load_elite_genome(self) -> Optional[Any]:
        try:
            if BEST_GENOME_PATH.exists():
                with open(BEST_GENOME_PATH, "r") as f:
                    data = json.load(f)
                genome = CommanderGenome(
                    genome_id=data.get("genome_id", "ELITE-LOADED"),
                    generation=data.get("generation", 0),
                    action_weights=data.get("action_weights", {}),
                    synergy_map={
                        tuple(k.split("|")): v
                        for k, v in data.get("synergy_map", {}).items()
                    },
                    mutation_rate=data.get("mutation_rate", 0.15),
                )
                genome.fitness_score = data.get("fitness_score", 0.0)
                logger.info(f"Elite genome loaded from {BEST_GENOME_PATH}")
                return genome
        except Exception as e:
            logger.warning(f"Failed to load elite genome: {e}")
        return None

    def _dict_to_phase_params(self, d: Dict) -> Any:
        from brain.reasoning.evolutionary_coagen import PhaseParameters
        return PhaseParameters(
            speed=d.get("speed", 1.0),
            confidence_threshold=d.get("confidence_threshold", 0.7),
            resource_efficiency=d.get("resource_efficiency", 0.8),
        )

    def _save_best_genome(self) -> None:
        if not self.best_genome:
            return
        try:
            data = self.best_genome.to_dict()
            with open(BEST_GENOME_PATH, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Best genome saved to {BEST_GENOME_PATH}")
        except Exception as e:
            logger.error(f"Failed to save best genome: {e}")

    def _adapt_mutation_rate(self) -> None:
        window = self.success_rate_window
        if len(self.episode_successes) < window:
            return
        recent_success = self.episode_successes[-window:]
        success_rate = sum(recent_success) / len(recent_success)
        if success_rate > 0.8:
            self.current_mutation_rate *= 0.90
            logger.info(f"Blue mutation rate DECREASED to {self.current_mutation_rate:.4f} (exploiting)")
        elif success_rate < 0.5:
            self.current_mutation_rate *= 1.20
            logger.info(f"Blue mutation rate INCREASED to {self.current_mutation_rate:.4f} (exploring)")
        if len(self.red_survival_rates) >= window and self.coevolution:
            recent_survival = self.red_survival_rates[-window:]
            survival_rate = sum(recent_survival) / len(recent_survival)
            if survival_rate < 0.5:
                self.coevolution.red_mutation_rate *= 1.20
                logger.info(f"Red mutation rate INCREASED to {self.coevolution.red_mutation_rate:.4f} (evading better)")

    def _print_dashboard(self, episode: int) -> None:
        if episode % 10 != 0:
            return
        window = min(10, len(self.episode_rewards))
        recent_rewards = self.episode_rewards[-window:] if window > 0 else [0.0]
        avg_reward = sum(recent_rewards) / len(recent_rewards) if recent_rewards else 0.0
        window_s = min(10, len(self.episode_successes))
        recent_successes = self.episode_successes[-window_s:] if window_s > 0 else []
        success_rate = (sum(recent_successes) / len(recent_successes) * 100) if recent_successes else 0.0
        best_novelty = 0.0
        if self.best_genome and hasattr(self.best_genome, 'fitness_score'):
            best_novelty = self.best_genome.fitness_score
        print("\n" + "=" * 70)
        print(f"ULTRONE TRAINING DASHBOARD - Episode {episode}/{self.num_episodes}")
        print("=" * 70)
        print(f"  Episode #          : {episode}")
        print(f"  Success Rate       : {success_rate:.1f}%")
        print(f"  Avg Reward         : {avg_reward:.1f}")
        print(f"  Mutation Rate      : {self.current_mutation_rate:.4f}")
        print(f"  Best Novelty Score : {best_novelty:.3f}")
        print(f"  Generation         : {self.generation}")
        print("=" * 70)
        window_survival = min(10, len(self.red_survival_rates))
        recent_survival = self.red_survival_rates[-window_survival:] if window_survival > 0 else []
        red_survival_rate = (sum(recent_survival) / len(recent_survival) * 100) if recent_survival else 0.0
        try:
            from viz.telemetry_dashboard import update_dashboard
            update_dashboard(
                episode=episode,
                success_rate=success_rate,
                mutation_rate=self.current_mutation_rate,
                avg_reward=avg_reward,
                novelty_score=best_novelty,
                red_survival_rate=red_survival_rate,
            )
        except Exception as e:
            logger.debug(f"Telemetry dashboard update skipped: {e}")

    def _gate_action(self, blue_action, obs):
        """Independent pre-execution safety enforcement.

        Audit P0 fix: previously ROE/constraint violations only produced
        negative reward AFTER execution. The core SafetyGate now blocks
        violating orders BEFORE they reach the environment. This gate is
        independent of the proposing genome (it reads asset state directly
        from the observation), so the planner cannot certify its own order.
        """
        if blue_action is None:
            return None
        try:
            from core.contracts import ActionOrder, AssetSnapshot, WorldEstimate
            from core.safety_gate import SafetyConfig, SafetyGate
        except Exception as e:  # graceful degradation if core unavailable
            logger.debug(f"Safety gate unavailable: {e}")
            return blue_action

        gate = SafetyGate(SafetyConfig(blacklisted_actions=self._hard_blacklist))

        def _snapshot(asset_type):
            assets = (obs.get("blue_assets") or {}).get(asset_type) or [{}]
            asset = assets[0]
            pos = asset.get("position")
            return AssetSnapshot(
                asset_type=asset_type,
                position=tuple(pos) if pos else None,
                fuel=float(asset.get("fuel", 1.0)),
                ammo=int(asset.get("ammo", 0)),
                range=float(asset.get("range", 9999.0)),
            )

        # Environment observations expose ground truth; belief confidence
        # for engagement-confidence rules is therefore maximal here.
        estimate = WorldEstimate(
            contacts=[], primary_target_position=blue_action.get("target"),
            primary_target_confidence=1.0,
            n_feeds_generated=0, n_feeds_received=0,
        )

        # Swarm hierarchical COA: gate each fleet entry individually.
        if blue_action.get("type") == "swarm":
            filtered = []
            for entry in blue_action.get("swarm_fleet", []):
                order = ActionOrder(
                    action=entry.get("action", "observe"),
                    asset_type=entry.get("asset_type", "drone"),
                    target=entry.get("target"),
                    source_coa_id="swarm",
                )
                verdict = gate.evaluate(order, estimate, _snapshot(order.asset_type))
                self._safety_stats["proposed"] += 1
                if verdict.approved:
                    filtered.append(entry)
                else:
                    self._safety_stats["blocked"] += 1
                    self._safety_stats["fleet_blocked"] += 1
                    logger.warning(f"Safety gate blocked fleet order: {verdict.reason}")
            blue_action["swarm_fleet"] = filtered
            return blue_action

        # Legacy single-order COA.
        order = ActionOrder(
            action=str(blue_action.get("action", "")),
            asset_type=str(blue_action.get("asset_type", "drones")),
            target=blue_action.get("target"),
            source_coa_id="legacy",
        )
        verdict = gate.evaluate(order, estimate, _snapshot(order.asset_type))
        self._safety_stats["proposed"] += 1
        if not verdict.approved:
            self._safety_stats["blocked"] += 1
            logger.warning(f"Safety gate blocked order: {verdict.reason}")
            return None
        return blue_action

    def _run_analysis(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        """Run battlefield analysis & 3D scene generation on an observation."""
        try:
            units = _entities_from_observation(obs)
            contacts = None
            self.last_units = units
            self.last_contacts = contacts
            analysis = self.battlefield_analyzer.analyze(units, contacts, grid_size=(100, 100))
            self.last_analysis = analysis
            if self._api_server is not None and hasattr(self._api_server, 'publish_analysis'):
                self._api_server.publish_analysis(analysis)
            return analysis
        except Exception as e:
            logger.warning(f"Battlefield analysis failed: {e}")
            return {}

    def run(self) -> Dict[str, Any]:
        logger.info(f"Starting ULTRONE training: {self.num_episodes} episodes")
        if self.seed is not None:
            import numpy as np
            random.seed(self.seed)
            np.random.seed(self.seed % (2 ** 32))
            logger.info(f"Reproducibility: seeded global RNGs with seed={self.seed}")
        elite = self._load_elite_genome()
        env = BattlefieldEnv()
        self._current_env = env

        if self.use_coevolution and self.coevolution is None:
            blue_commander = None
            if elite is not None and hasattr(elite, 'spawn_asset_micro_genomes'):
                blue_commander = elite
            else:
                blue_commander = CommanderGenome(
                    genome_id=f"BLUE-{random.randint(10000, 99999)}",
                    action_weights={a: random.uniform(0.5, 1.0) for a in ["strike", "jam", "move", "engage", "locate", "assess"]},
                    synergy_map={(a, b): random.uniform(0.0, 1.0) for i, a in enumerate(["strike", "jam", "move", "engage", "locate", "assess"]) for b in ["strike", "jam", "move", "engage", "locate", "assess"][i+1:]},
                    mutation_rate=self.current_mutation_rate,
                )
            red_genome = RedForceGenome(genome_id=f"RED-{random.randint(10000, 99999)}")
            self.coevolution = CoevolutionEngine(sample_size=3)
            self.coevolution.initialize_blue(blue_commander)
            self.coevolution.initialize_red(red_genome)

        if self._briefing_generator is None:
            try:
                from generative.commander_briefing import CommanderBriefingGenerator, log_training_summary
                self._briefing_generator = CommanderBriefingGenerator()
                log_training_summary()
            except Exception as e:
                logger.debug(f"Briefing generator unavailable: {e}")

        self._llm_commander = None
        self._secretary_council = None
        self._current_directive = None
        try:
            from brain.learning.llm_commander import LLMCommander
            from brain.reasoning.secretary_council import SecretaryCouncil, analyze_red_behavior, analyze_blue_attrition
            self._llm_commander = LLMCommander()
            self._secretary_council = SecretaryCouncil()
            self._analyze_red_behavior = analyze_red_behavior
            self._analyze_blue_attrition = analyze_blue_attrition
        except Exception as e:
            logger.debug(f"Hybrid LLM components unavailable: {e}")

        self._intervention_manager = None
        self._api_server = None
        try:
            from comms.api_server import InterventionManager, create_api_server
            self._intervention_manager = InterventionManager()
            self._api_server = create_api_server(self, self._intervention_manager)
            if self._api_server:
                self._api_server.start()
        except Exception as e:
            logger.debug(f"Operational API unavailable: {e}")

        overall_best_fitness = self.best_fitness
        overall_best_genome = elite

        for episode in range(1, self.num_episodes + 1):
            obs = env.reset()
            blue_commander = self.coevolution.blue_active if self.use_coevolution and self.coevolution else None
            red_genome = self.coevolution.red_active if self.use_coevolution and self.coevolution else None

            if self._intervention_manager is not None:
                constraints = self._intervention_manager.get_constraints()
                if constraints:
                    logger.info(f"Applying {len(constraints)} intervention constraints")
                    if 'force_novelty_weight' in constraints:
                        if self._secretary_council is not None:
                            from brain.reasoning.secretary_council import StrategicDirective
                            self._current_directive = StrategicDirective(
                                weights={
                                    'effectiveness_weight': 1.0 - constraints['force_novelty_weight'],
                                    'efficiency_weight': 0.0,
                                    'novelty_weight': constraints['force_novelty_weight'],
                                },
                                focus='human_override',
                                notes='Human forced novelty via API'
                            )
                    if 'blacklist_action' in constraints and blue_commander is not None:
                        blacklisted = constraints['blacklist_action'].upper()
                        if hasattr(blue_commander, 'action_weights'):
                            for action in list(blue_commander.action_weights.keys()):
                                if action.upper() == blacklisted:
                                    blue_commander.action_weights[action] = 0.0

            coa_gen = EvolutionaryCOAGenerator()
            if blue_commander is not None:
                coa_gen.active_genome = blue_commander
                coa_gen.population = [blue_commander]
                coa_gen._initialized = True
            elif elite is not None:
                coa_gen.active_genome = elite
                coa_gen.population = [elite]
                coa_gen._initialized = True

            base_mutation = self.current_mutation_rate
            if self._current_directive:
                focus = self._current_directive.focus
                if focus in ("novelty", "counter_ecm"):
                    self.current_mutation_rate = min(0.30, max(0.15, base_mutation * 1.5))
                elif focus in ("efficiency",):
                    self.current_mutation_rate = max(0.01, min(0.08, base_mutation * 0.5))
                elif focus in ("counter_evade",):
                    self.current_mutation_rate = max(0.08, min(0.20, base_mutation * 1.1))

            total_reward = 0.0
            success = False
            red_survived = True
            done = False
            step = 0
            telemetry_accum = TelemetryAccumulator()

            while not done and step < self.max_steps_per_episode:
                step += 1
                target_info = {
                    "domain": obs.get("red_force", {}).get("type", "unknown"),
                    "type": obs.get("red_force", {}).get("type", "unknown"),
                }
                context = {"observation": obs}
                coa = coa_gen.generate_evolved_coa(target_info, context)

                blue_action = None
                if coa and coa.phases:
                    if hasattr(coa, 'swarm_fleet') and coa.swarm_fleet:
                        fleet = []
                        for micro in coa.swarm_fleet:
                            asset_action = {
                                "asset_type": micro.asset_type,
                                "action": "strike" if micro.aggressiveness > 0.6 else "move",
                                "target": (int(obs.get("red_force", {}).get("position", (50, 50))[0] + random.randint(-10, 10)),
                                           int(obs.get("red_force", {}).get("position", (50, 50))[1] + random.randint(-10, 10)))
                            }
                            fleet.append(asset_action)
                        blue_action = {
                            "type": "swarm",
                            "swarm_fleet": fleet,
                            "commander_genome": coa.commander_genome,
                        }
                    else:
                        # Legacy single-COA mode: pick first executable action
                        first_action = None
                        for phase in coa.phases:
                            if phase in ("strike", "jam", "move", "resupply"):
                                first_action = phase
                                break
                        if first_action is not None:
                            asset_type = {
                                "strike": "missiles",
                                "move": "drones",
                                "jam": "jammers",
                                "resupply": "missiles",
                            }.get(first_action, "drones")
                            blue_action = {
                                "action": first_action,
                                "asset_type": asset_type,
                                "target": obs.get("red_force", {}).get("position", (50, 50)),
                            }

                # ---- Independent pre-execution safety enforcement ----
                if self._intervention_manager is not None:
                    constraints = self._intervention_manager.get_constraints()
                    blacklisted = constraints.get("blacklist_action")
                    if blacklisted:
                        self._hard_blacklist.add(str(blacklisted).lower())

                gated = self._gate_action(blue_action, obs)
                if blue_action is not None and gated is None:
                    logger.info(
                        f"Episode {episode}: order blocked by safety gate at step {step}"
                    )
                blue_action = gated

                # ---- Determine Red Force action from evolved genome ----
                red_action = None
                if red_genome is not None:
                    red_action = {
                        "evade": red_genome.should_evade(),
                        "ecm": red_genome.should_trigger_ecm(),
                        "ecm_noise": red_genome.ecm_noise_level,
                        "target": None,
                    }

                # ---- Execute action in the environment ----
                obs, reward, done, info = env.step(blue_action, red_action)
                total_reward += reward
                telemetry_accum.add_step(info, step)

                # Track red survival
                red_health = obs.get("red_force", {}).get("health", 0)
                red_survived = red_health > 0

                # Log ROE violations but do NOT end the episode.
                # Ending early prevents evolution from learning away from
                # the violating behavior; the large negative reward already
                # penalizes the genome so it evolves to avoid it.
                if info.get("roe_violation", False):
                    logger.warning(
                        f"Episode {episode}: ROE violation at step {step} "
                        f"(penalty applied, episode continues)"
                    )

                # Check for mission success
                if done and red_health <= 0:
                    success = True

            # ---- Episode complete: evaluate fitness & evolve ----
            final_telemetry = telemetry_accum.finalize(step, red_survived)

            if self.use_coevolution and self.coevolution is not None:
                if blue_commander is not None and red_genome is not None:
                    red_telemetry = {red_genome.genome_id: final_telemetry}
                    directive_weights = (
                        self._current_directive.weights if self._current_directive else None
                    )
                    blue_fitness = self.coevolution.evaluate_blue_fitness(
                        blue_commander,
                        self.coevolution.red_population,
                        red_telemetry,
                        directive_weights,
                    )
                    self.coevolution.evaluate_red_fitness(
                        red_genome,
                        red_survived,
                        final_telemetry.get("ecm_active", False),
                        step,
                    )

                    if blue_fitness > self.best_fitness:
                        self.best_fitness = blue_fitness
                        self.best_genome = blue_commander
                        self._save_best_genome()

                    # Evolve generations periodically
                    if episode % 10 == 0:
                        evolved_blue = self.coevolution.evolve_blue_generation()
                        self.coevolution.evolve_red_generation()
                        if evolved_blue is not None:
                            self.generation = evolved_blue.generation
                            logger.info(
                                f"Coevolution advanced to generation {self.generation} "
                                f"(blue fitness {evolved_blue.fitness_score:.3f})"
                            )

            # Track episode metrics
            self.episode_rewards.append(total_reward)
            self.episode_successes.append(success)
            self.red_survival_rates.append(1.0 if red_survived else 0.0)

            self._adapt_mutation_rate()
            self._print_dashboard(episode)

            # Run battlefield analysis & publish to API server
            if episode % 5 == 0:
                self._run_analysis(obs)

            # Generate periodic commander briefing
            if self._briefing_generator is not None and episode % 20 == 0:
                window = min(10, len(self.episode_successes))
                recent_successes = self.episode_successes[-window:] if window else [False]
                recent_rewards = self.episode_rewards[-window:] if window else [0.0]
                recent_survival = self.red_survival_rates[-window:] if window else [0.0]
                briefing_telemetry = {
                    "success_rate": sum(recent_successes) / len(recent_successes),
                    "avg_reward": sum(recent_rewards) / len(recent_rewards),
                    "mutation_rate": self.current_mutation_rate,
                    "best_novelty": self.best_genome.fitness_score if self.best_genome else 0.0,
                    "red_survival_rate": sum(recent_survival) / len(recent_survival),
                    "generation": self.generation,
                }
                self._briefing_generator.write_briefing(episode, briefing_telemetry)

            logger.info(
                f"Episode {episode}/{self.num_episodes}: "
                f"reward={total_reward:.1f}, success={success}, red_survived={red_survived}"
            )

        # ---- Training complete ----
        if self._api_server is not None:
            try:
                self._api_server.stop()
            except Exception as e:
                logger.debug(f"API server stop failed: {e}")

        logger.info(f"Training complete. Best fitness: {self.best_fitness:.3f}")
        return self.get_training_summary()

    def orient_phase(self, threatening: List[Any], tick: int) -> List[Any]:
        """Orient: detect enemy patterns and trigger active evolution mid-battle."""
        detected_patterns = self.pattern_recognizer.detect_patterns_in_contacts(threatening)
        for pattern in detected_patterns:
            if pattern.confidence > 0.8:
                mutated = self.active_evolution.process_pattern(pattern, tick, threatening)
                if mutated:
                    self._mutations_performed += 1
                    self._active_mutations[pattern.domain] = (
                        self._active_mutations.get(pattern.domain, 0) + 1
                    )
                    logger.info(
                        f"Active evolution triggered: {pattern.description} "
                        f"(confidence {pattern.confidence:.2f})"
                    )
        return detected_patterns

    def _get_active_capabilities(self) -> Dict[str, Any]:
        """Return current active-evolution capability values."""
        caps = {}
        for name in ("target_confirmation_threshold", "f2t2ea_phase_speed", "bda_rigor"):
            caps[name] = self.active_evolution.get_capability(name)
        return caps

    def get_training_summary(self) -> Dict[str, Any]:
        """Build summary dict used by main.py and the API server."""
        total = len(self.episode_successes)
        success_rate = (sum(self.episode_successes) / total) if total else 0.0
        avg_reward = (sum(self.episode_rewards) / len(self.episode_rewards)) if self.episode_rewards else 0.0
        return {
            "total_episodes": total,
            "success_rate": success_rate,
            "avg_reward": avg_reward,
            "best_fitness": self.best_fitness or 0.0,
            "best_genome_id": self.best_genome.genome_id if self.best_genome else None,
            "final_mutation_rate": self.current_mutation_rate,
            "generation": self.generation,
            "red_survival_rate": (
                sum(self.red_survival_rates) / len(self.red_survival_rates)
                if self.red_survival_rates else 0.0
            ),
            "mutations_performed": self._mutations_performed,
            "active_capabilities": self._get_active_capabilities(),
        }


def _entities_from_observation(obs: Dict[str, Any]) -> List[Any]:
    """Convert a BattlefieldEnv observation into entity-like objects.

    Builds minimal unit-like objects with team, position, health, and type
    attributes that the BattlefieldAnalyzer can consume.
    """
    class _Entity:
        def __init__(self, eid: str, team: str, position: Any, health: float, etype: str):
            self.unit_id = eid
            self.team = team
            self.position = position
            self.health = health
            self.unit_type = etype
            self.capability = 1.0

    entities: List[Any] = []

    # Red force
    red = obs.get("red_force", {})
    if red:
        entities.append(_Entity(
            eid="red_force_main",
            team="red",
            position=red.get("position", (50, 50)),
            health=red.get("health", 100),
            etype=red.get("type", "unknown"),
        ))

    # Blue assets
    blue = obs.get("blue_assets", {})
    for asset_type, assets in blue.items():
        for i, asset in enumerate(assets):
            entities.append(_Entity(
                eid=f"{asset_type}_{i}",
                team="blue",
                position=asset.get("position", (50, 50)),
                health=asset.get("health", 100),
                etype=asset_type,
            ))

    # Supply nodes (neutral infrastructure)
    supply_nodes = obs.get("supply_nodes", {})
    for sid, sn in supply_nodes.items():
        entities.append(_Entity(
            eid=sid,
            team=sn.get("team", "neutral"),
            position=sn.get("position", (50, 50)),
            health=sn.get("health", 100),
            etype="supply_node",
        ))

    return entities
