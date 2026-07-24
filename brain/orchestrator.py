# Copyright (c) Ultrone Contributors. All rights reserved.
"""Brain orchestrator - central military C2 system with OODA loop."""

import logging
import random
from typing import Dict, List, Optional, Any

from .learning import EvolutionLab, EvolutionConfig, AgentEvolver, PatternRecognizer
from .perception import SituationalAwareness
from .learning import ThreatPattern
from .reasoning import (
    TacticalEngine, KillChain, CompositeKillChain,
    DomainEngagement, CompositePhase,
    KillChainCapsule, ActiveEvolutionManager,
)
from .strategy import Doctrine, OperationalPlanner, StrategicPlanner
from ..config import MilitaryConfig
from ..config.doctrine_presets import DoctrineType, get_doctrine_preset
from ..sim import WorldState
from ..comms import MessageBus
from ..generative import (
    TacticalSynthesizer, ScenarioGenerator,
    AdversarialEmulator, ReportGenerator,
)

logger = logging.getLogger("Ultrone.Brain.Orchestrator")

<<<<<<< Updated upstream
=======
# Ensure project root is on sys.path for top-level imports
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Default paths
MEMORY_DIR = Path(__file__).parent.parent / "memory"
BEST_GENOME_PATH = MEMORY_DIR / "best_genome.json"
COMMANDER_LOG_PATH = MEMORY_DIR / "commander_log.txt"


class TelemetryAccumulator:
    """
    Accumulates step-level telemetry across an episode with time-weighted averaging.
    
    Later steps receive higher weight (linear ramp: 1.0 + 0.1*step_idx),
    so that end-game maneuvers matter more than early positioning.
    
    Phase 6 additions:
    - fuel_consumed: total fuel burned in episode
    - supply_nodes_alive & total_supply_nodes: supply node state tracking
    - supply_penalty_active: whether supply penalty was triggered
    - avg_fuel: average fuel across blue assets at end
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
        # Phase 6: fuel & supply tracking
        self.fuel_consumed: float = 0.0
        self.supply_nodes_alive: int = 2
        self.total_supply_nodes: int = 2
        self.supply_penalty_active: bool = False
        self.avg_fuel: float = 1.0
        # Time-weighted accumulators
        self._weighted_accuracy: float = 0.0
        self._weight_sum: float = 0.0
    
    def add_step(self, step_telemetry: Dict[str, Any], step_idx: int) -> None:
        """Accumulate one step of telemetry with linear time-weighting."""
        weight = 1.0 + 0.1 * step_idx  # later steps matter more
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
        # Phase 6: accumulate fuel
        self.fuel_consumed += step_telemetry.get("fuel_consumed", 0.0)
        # Track time-weighted accuracy
        step_hit = 1.0 if step_telemetry.get("hits", 0) > 0 else 0.0
        self._weighted_accuracy += weight * step_hit
        self._weight_sum += weight
    
    def finalize(self, total_steps: int, red_survived: bool) -> Dict[str, Any]:
        """Produce aggregated telemetry dict at episode end."""
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
            # Phase 6 fields
            "fuel_consumed": self.fuel_consumed,
            "supply_nodes_alive": self.supply_nodes_alive,
            "total_supply_nodes": self.total_supply_nodes,
            "supply_penalty_active": self.supply_penalty_active,
            "avg_fuel": self.avg_fuel,
        }

>>>>>>> Stashed changes

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
    
    def __init__(self, config: Optional[MilitaryConfig] = None):
        self.config = config or MilitaryConfig()
        
        # Initialize evolution system
        self.evolution_lab = EvolutionLab()
        self.evolution_lab.initialize(agent_id="orchestrator")
        
        self.agent_evolver = AgentEvolver(self.evolution_lab)
        
        # Initialize perception
        self.situational_awareness = SituationalAwareness()
        
        # Initialize reasoning
        self.tactical_engine = TacticalEngine()
        self.kill_chain = KillChain()
        self.composite_chains: Dict[str, CompositeKillChain] = {}
        
        # Initialize active evolution manager
        # This is the key: manages real-time mutation during battle
        self.active_evolution = ActiveEvolutionManager(
            self.evolution_lab.genome_engine,
            self.kill_chain
        )
        
        # Initialize pattern recognizer for orient phase
        self.pattern_recognizer = PatternRecognizer()
        
        # Initialize strategy
        self.doctrine = Doctrine(get_doctrine_preset(DoctrineType.BALANCED))
        self.operational_planner = OperationalPlanner()
        self.strategic_planner = StrategicPlanner()
        
        # Communications
        self.message_bus = MessageBus()
        
        # Generative AI systems
        self.tactical_synthesizer = TacticalSynthesizer()
        self.scenario_generator = ScenarioGenerator()
        self.adversarial_emulator = AdversarialEmulator()
        self.report_generator = ReportGenerator()
        
        # OODA tracking
        self._ooda_cycle = 0
        self._generative_tick = 0
        self._mutations_performed = 0
        self._active_mutations: Dict[str, int] = {}  # domain -> ticks since last mutation
    
    async def initialize(self) -> None:
        """Initialize all systems."""
        await self.message_bus.start()
        # Initialize the kill chain capsule
        self.active_evolution.initialize_capsule("orchestrator")
        logger.info("Orchestrator initialized with balanced doctrine and active evolution")
    
    async def process_tick(self, world_state: WorldState, tick: int) -> Dict[str, Any]:
        """
        Process one simulation tick with OODA loop.
        
        ACTIVE EVOLUTION HAPPENS HERE:
        During Orient phase, if pattern_recognizer detects enemy tactic with >80% confidence,
        immediately trigger directed_mutation() on KillChainCapsule to lower
        target_confirmation_threshold or increase f2t2ea_phase_speed for that specific threat.
        """
        self._ooda_cycle += 1
        
        # O - OBSERVE: Update COP with sensor data
        units = list(world_state.units.values())
        self.situational_awareness.update([], units)
        
        threatening = self.situational_awareness.get_threatening_contacts()
        
        # O - ORIENT: Check for recognized patterns AND IMMEDIATELY MUTATE
        # This is where active evolution happens - mid-battle!
        detected_patterns = self.orient_phase(threatening, tick)
        
        # D - DECIDE: Generate COAs using the now-evolved parameters
        assessments = self.tactical_engine.decide(threatening, units)
        
        # A - ACT: Execute orders with evolved tactics
        results = self.tactical_engine.execute({u.unit_id: u for u in units})
        
        # Log actions for evolution
        for assessment in assessments:
            self.evolution_lab.log_action(
                action="tactical_assessment",
                domain="all",
                success=random.random() > 0.2,
                response_time_ms=100.0,
                context={"assessment": assessment.to_dict()},
            )
<<<<<<< Updated upstream
=======
            logger.info(f"Elite genome loaded from {BEST_GENOME_PATH}")
            return genome
        except Exception as e:
            logger.warning(f"Failed to load elite genome: {e}")
            return None

    def _dict_to_phase_params(self, d: Dict) -> Any:
        """Convert dict to PhaseParameters dataclass."""
        from brain.reasoning.evolutionary_coagen import PhaseParameters
        return PhaseParameters(
            speed=d.get("speed", 1.0),
            confidence_threshold=d.get("confidence_threshold", 0.7),
            resource_efficiency=d.get("resource_efficiency", 0.8),
        )

    def _save_best_genome(self) -> None:
        """Save the best genome to persistent memory."""
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
        """
        Dynamically adjust mutation rates for both Blue and Red based on recent performance.
        
        Blue rules:
        - If last 10 episodes have >80% success: DECREASE by 10% (exploit)
        - If last 10 episodes have <50% success: INCREASE by 20% (explore)
        
        Red rules:
        - If last 10 episodes have <50% Red survival: INCREASE by 20% (evade better)
        """
        window = self.success_rate_window
        if len(self.episode_successes) < window:
            return
        
        recent_success = self.episode_successes[-window:]
        success_rate = sum(recent_success) / len(recent_success)
        
        # Adaptive Blue mutation rate
        if success_rate > 0.8:
            self.current_mutation_rate *= 0.90
            logger.info(f"Blue mutation rate DECREASED to {self.current_mutation_rate:.4f} (exploiting)")
        elif success_rate < 0.5:
            self.current_mutation_rate *= 1.20
            logger.info(f"Blue mutation rate INCREASED to {self.current_mutation_rate:.4f} (exploring)")
        
        # Adaptive Red mutation rate based on survival
        if len(self.red_survival_rates) >= window:
            recent_survival = self.red_survival_rates[-window:]
            survival_rate = sum(recent_survival) / len(recent_survival)
            if survival_rate < 0.5:
                self.coevolution.red_mutation_rate *= 1.20
                logger.info(f"Red mutation rate INCREASED to {self.coevolution.red_mutation_rate:.4f} (evading better)")

    def _print_dashboard(self, episode: int) -> None:
        """Print clean dashboard every 10 episodes."""
        if episode % 10 != 0:
            return
        
        window = min(10, len(self.episode_rewards))
        recent_rewards = self.episode_rewards[-window:] if window > 0 else [0.0]
        avg_reward = sum(recent_rewards) / len(recent_rewards) if recent_rewards else 0.0
        
        window_s = min(10, len(self.episode_successes))
        recent_successes = self.episode_successes[-window_s:] if window_s > 0 else []
        success_rate = (sum(recent_successes) / len(recent_successes) * 100) if recent_successes else 0.0
        
        best_novelty = 0.0
        # Access best genome's fitness as proxy for novelty score
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
        
        # Compute red survival rate for this window
        window_survival = min(10, len(self.red_survival_rates))
        recent_survival = self.red_survival_rates[-window_survival:] if window_survival > 0 else []
        red_survival_rate = (sum(recent_survival) / len(recent_survival) * 100) if recent_survival else 0.0
        
        # Push telemetry to live visualization
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

    def run(self) -> Dict[str, Any]:
        """
        Execute the master training loop.
        
        Returns:
            Training statistics summary
        """
        logger.info(f"Starting ULTRONE training: {self.num_episodes} episodes")
        
        # Try to load elite genome from memory
        elite = self._load_elite_genome()
        
        # Initialize environment and evolutionary engine
        env = self.BattlefieldEnv()
        
        # Initialize coevolution engine
        if self.use_coevolution and not hasattr(self, 'coevolution'):
            # Bootstrap populations from loaded elite or defaults
            blue_commander = None
            if hasattr(elite, 'spawn_asset_micro_genomes'):
                blue_commander = elite
            else:
                blue_commander = self.CommanderGenome(
                    genome_id=f"BLUE-{random.randint(10000, 99999)}",
                    action_weights={a: random.uniform(0.5, 1.0) for a in ["strike", "jam", "move", "engage", "locate", "assess"]},
                    synergy_map={(a, b): random.uniform(0.0, 1.0) for i, a in enumerate(["strike", "jam", "move", "engage", "locate", "assess"]) for b in ["strike", "jam", "move", "engage", "locate", "assess"][i+1:]},
                    mutation_rate=self.current_mutation_rate,
                )
            red_genome = self.RedForceGenome(genome_id=f"RED-{random.randint(10000, 99999)}")
            self.coevolution = self.CoevolutionEngine(sample_size=3)
            self.coevolution.initialize_blue(blue_commander)
            self.coevolution.initialize_red(red_genome)
        
        # Initialize post-hoc commander briefing generator
        if self._briefing_generator is None:
            try:
                from generative.commander_briefing import CommanderBriefingGenerator, log_training_summary
                self._briefing_generator = CommanderBriefingGenerator()
                log_training_summary()
            except Exception as e:
                logger.debug(f"Briefing generator unavailable: {e}")
        
        # Initialize hybrid LLM components
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
        
        # Initialize Operational API Server (HITL + XAI)
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
        
        # Track best across all episodes
        overall_best_fitness = self.best_fitness
        overall_best_genome = elite
        
        for episode in range(1, self.num_episodes + 1):
            # Reset environment
            obs = env.reset()
            
            # Check for human interventions before running this episode
            if hasattr(self, '_intervention_manager'):
                constraints = self._intervention_manager.get_constraints()
                if constraints:
                    logger.info(f"Applying {len(constraints)} intervention constraints")
                    # Force novelty weight override
                    if 'force_novelty_weight' in constraints:
                        if hasattr(self, '_secretary_council') and self._secretary_council:
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
                    # Blacklist actions (e.g., blacklist STRIKE)
                    if 'blacklist_action' in constraints:
                        blacklisted = constraints['blacklist_action'].upper()
                        if blue_commander and hasattr(blue_commander, 'action_weights'):
                            # Zero out the blacklisted action weight
                            for action in list(blue_commander.action_weights.keys()):
                                if action.upper() == blacklisted:
                                    blue_commander.action_weights[action] = 0.0
            
            # Get current Blue and Red genomes
            blue_commander = self.coevolution.blue_active if self.use_coevolution else None
            red_genome = self.coevolution.red_active if self.use_coevolution else None
            
            # Initialize evolutionary engine for this episode
            coa_gen = self.EvolutionaryCOAGenerator()
            if blue_commander:
                coa_gen.active_genome = blue_commander
                coa_gen.population = [blue_commander]
                coa_gen._initialized = True
            elif elite:
                coa_gen.active_genome = elite
                coa_gen.population = [elite]
                coa_gen._initialized = True
            
            # Apply directive -> mutation rate mapping before episode
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
            
            # Initialize step-level telemetry accumulator
            telemetry_accum = TelemetryAccumulator()
            
            # Episode loop
            while not done and step < self.max_steps_per_episode:
                step += 1
                
                # Generate Blue COA
                target_info = {
                    "domain": obs.get("red_force", {}).get("type", "unknown"),
                    "type": obs.get("red_force", {}).get("type", "unknown"),
                }
                context = {"observation": obs}
                coa = coa_gen.generate_evolved_coa(target_info, context)
                
                # Extract Blue action from COA phases
                blue_action = None
                swarm_coa = None
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
                        swarm_coa = {
                            "type": "swarm",
                            "swarm_fleet": fleet,
                            "commander_genome": blue_commander.to_dict() if blue_commander else None,
                        }
                        blue_action = swarm_coa
                    else:
                        for phase in coa.phases:
                            if phase in ["strike", "jam", "move"]:
                                blue_action = {"action": phase, "asset_type": "missiles" if phase == "strike" else "jammers"}
                                if phase == "move":
                                    blue_action["target"] = (50, 50)
                                break
                
                # Generate Red action
                red_action = None
                if red_genome:
                    red_action = {
                        "evade": red_genome.should_evade(),
                        "ecm": red_genome.should_trigger_ecm(),
                        "ecm_noise": red_genome.ecm_noise_level,
                        "target": None,
                    }
                
                # Step environment with both Blue and Red actions
                try:
                    obs, reward, done, info = env.step(blue_action, red_action)
                    total_reward += reward
                    
                    # Check if target was destroyed (success)
                    if done and reward > 0:
                        success = True
                        red_survived = False
                
                except Exception as e:
                    logger.error(f"Error during environment step: {e}")
                    break
                
                # Accumulate step telemetry
                step_telemetry = {
                    "hits": 1 if (done and reward > 0) else 0,
                    "attempts": 1,
                    "weapons_used": 1 if (blue_action and isinstance(blue_action, dict) and blue_action.get("action") == "strike") else 0,
                    "weapons_allocated": 3,
                    "actions_used": coa.phases if coa else [],
                    "blue_on_blue": 1 if info.get("swarm_collisions", 0) > 0 else 0,
                    "collision_count": info.get("swarm_collisions", 0),
                    "red_survived": red_survived,
                    "ecm_active": info.get("ecm_active", False),
                    "fuel_consumed": info.get("fuel_consumed", 0.0),
                }
                telemetry_accum.add_step(step_telemetry, step - 1)
            
            # Finalize accumulated telemetry and apply fitness at episode end
            # Phase 6: capture supply node state from final observation
            supply_nodes_data = obs.get("supply_nodes", {})
            telemetry_accum.supply_nodes_alive = sum(
                1 for sn in supply_nodes_data.values() if sn.get("alive", False)
            )
            telemetry_accum.total_supply_nodes = len(supply_nodes_data)
            telemetry_accum.supply_penalty_active = obs.get("supply_penalty_active", False)
            
            # Compute average fuel across blue assets at episode end
            all_blue_assets = []
            for assets in obs.get("blue_assets", {}).values():
                all_blue_assets.extend(assets)
            if all_blue_assets:
                telemetry_accum.avg_fuel = sum(
                    a.get("fuel", 0.0) for a in all_blue_assets
                ) / len(all_blue_assets)
            
            agg_telemetry = telemetry_accum.finalize(step, red_survived)
            directive_weights = self._current_directive.weights if self._current_directive else None
            if blue_commander and self.use_coevolution:
                self.coevolution.evaluate_blue_fitness(
                    blue_commander, [red_genome],
                    {red_genome.genome_id: agg_telemetry},
                    directive=directive_weights
                )
            else:
                fitness = coa_gen.evaluate_fitness(coa_gen.active_genome, agg_telemetry)
            
            # Track best genome using finalized fitness
            current_fitness = blue_commander.fitness_score if blue_commander else fitness
            if current_fitness > overall_best_fitness:
                overall_best_fitness = current_fitness
                overall_best_genome = blue_commander or coa_gen.active_genome
                self.best_fitness = overall_best_fitness
                self.best_genome = overall_best_genome
            
            # Log structured directive-level impact metadata
            if self._current_directive:
                directive_log = json.dumps({
                    "episode": episode,
                    "directive_focus": self._current_directive.focus,
                    "effectiveness_weight": self._current_directive.weights.get("effectiveness_weight", 0.5),
                    "efficiency_weight": self._current_directive.weights.get("efficiency_weight", 0.3),
                    "novelty_weight": self._current_directive.weights.get("novelty_weight", 0.2),
                    "notes": self._current_directive.notes,
                    "mutation_rate_used": self.current_mutation_rate,
                    "episode_success": success,
                    "episode_reward": total_reward,
                })
                try:
                    COMMANDER_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
                    with open(COMMANDER_LOG_PATH, "a", encoding="utf-8") as f:
                        f.write(f"[DIRECTIVE] {directive_log}\n")
                except Exception as e:
                    logger.debug(f"Failed to write directive log: {e}")
            
            # Record episode results
            self.episode_rewards.append(total_reward)
            self.episode_successes.append(success)
            self.red_survival_rates.append(1.0 if red_survived else 0.0)
            
            # Evolve generation
            if self.use_coevolution and blue_commander:
                new_blue = self.coevolution.evolve_blue_generation()
                new_red = self.coevolution.evolve_red_generation()
                if new_blue:
                    self.generation = new_blue.generation
                elite = new_blue or blue_commander
            else:
                self.generation = coa_gen.active_genome.generation if coa_gen.active_genome else self.generation
                elite = coa_gen.active_genome
            
            # Adapt mutation rate
            self._adapt_mutation_rate()
            
            # Print dashboard
            self._print_dashboard(episode)
            
            # Hybrid LLM guidance every 20 episodes
            if episode % 20 == 0:
                window_survival = min(10, len(self.red_survival_rates))
                recent_survival = self.red_survival_rates[-window_survival:] if window_survival > 0 else []
                red_survival_rate = (sum(recent_survival) / len(recent_survival) * 100) if recent_survival else 0.0
                
                window_rewards = min(10, len(self.episode_rewards))
                recent_rewards = self.episode_rewards[-window_rewards:] if window_rewards > 0 else [0.0]
                avg_reward = sum(recent_rewards) / len(recent_rewards) if recent_rewards else 0.0
                
                window_s = min(10, len(self.episode_successes))
                recent_successes = self.episode_successes[-window_s:] if window_s > 0 else []
                success_rate = (sum(recent_successes) / len(recent_successes)) if recent_successes else 0.0
                
                best_novelty = 0.0
                if self.best_genome and hasattr(self.best_genome, 'fitness_score'):
                    best_novelty = self.best_genome.fitness_score
                
                telemetry = {
                    "episode": episode,
                    "success_rate": success_rate,
                    "avg_reward": avg_reward,
                    "mutation_rate": self.current_mutation_rate,
                    "red_survival_rate": red_survival_rate / 100.0,
                    "generation": self.generation,
                    "best_novelty": best_novelty,
                }
                
                # LLM Commander visual-grounding brief with multi-INT knowledge
                if self._llm_commander is not None:
                    try:
                        ascii_map = env.render_ascii_map()
                        # Phase 6: Build knowledge graph from observation for richer briefing
                        from brain.perception.knowledge_graph import MultiINTKnowledgeGraph
                        kg = MultiINTKnowledgeGraph()
                        kg.ingest_from_observation(obs)
                        knowledge_summary = kg.get_summary()
                        self._llm_commander.write_briefing(ascii_map, telemetry)
                    except Exception as e:
                        logger.debug(f"LLM commander brief failed: {e}")
                
                # Secretary Council strategic directive
                if self._secretary_council is not None:
                    try:
                        red_behavior = self._analyze_red_behavior(red_genome, self.red_survival_rates)
                        blue_attrition = self._analyze_blue_attrition(obs.get("blue_assets", {}))
                        directive = self._secretary_council.deliberate(telemetry, red_behavior, blue_attrition)
                        self._current_directive = directive
                        logger.info(f"Strategic directive: {directive.focus} - {directive.notes}")
                    except Exception as e:
                        logger.debug(f"Secretary council failed: {e}")
            
            # Post-hoc commander briefing every 20 episodes
            if self._briefing_generator is not None:
                from generative.commander_briefing import should_brief
                if should_brief(episode, interval=20):
                    window_survival = min(10, len(self.red_survival_rates))
                    recent_survival = self.red_survival_rates[-window_survival:] if window_survival > 0 else []
                    red_survival_rate = (sum(recent_survival) / len(recent_survival) * 100) if recent_survival else 0.0
                    
                    telemetry = {
                        "success_rate": (sum(self.episode_successes[-10:]) / len(self.episode_successes[-10:])) if len(self.episode_successes) >= 10 else (sum(self.episode_successes) / max(1, len(self.episode_successes))),
                        "avg_reward": avg_reward,
                        "mutation_rate": self.current_mutation_rate,
                        "red_survival_rate": red_survival_rate / 100.0,
                        "generation": self.generation,
                        "best_novelty": best_novelty,
                    }
                    self._briefing_generator.write_briefing(episode, telemetry)
        
        # Save best genome after all episodes
        if overall_best_genome:
            self.best_genome = overall_best_genome
            self.best_fitness = overall_best_fitness
            self._save_best_genome()
        
        # Final summary
        self._print_dashboard(self.num_episodes)
        
        summary = self.get_training_summary()
        logger.info(f"Training complete. Best fitness: {self.best_fitness:.3f}")
        return summary

    def get_training_summary(self) -> Dict[str, Any]:
        """Get training statistics summary."""
        if not self.episode_rewards:
            return {}
        
        total_episodes = len(self.episode_rewards)
        total_successes = sum(self.episode_successes)
        success_rate = total_successes / total_episodes if total_episodes > 0 else 0.0
        avg_reward = sum(self.episode_rewards) / total_episodes
>>>>>>> Stashed changes
        
        return {
            "tick": tick,
            "threats_detected": len(threatening),
            "assessments": len(assessments),
            "orders_executed": results.get("executed", 0),
            "mutations_this_tick": sum(1 for p in detected_patterns if p.confidence > 0.8),
            "active_capabilities": self._get_active_capabilities(),
        }
    
    def _get_active_capabilities(self) -> Dict[str, float]:
        """Get current evolved capabilities from the kill chain capsule."""
        return {
            "target_confirmation_threshold": self.active_evolution.get_capability("target_confirmation_threshold"),
            "f2t2ea_phase_speed": self.active_evolution.get_capability("f2t2ea_phase_speed"),
        }
    
    def orient_phase(self, threatening_contacts, tick: int) -> List[ThreatPattern]:
        """
        OODA Orient phase: Check for recognized enemy patterns.
        
        ACTIVE EVOLUTION TRIGGER:
        If pattern_recognizer detects an enemy tactic with >80% confidence,
        IMMEDIATELY trigger directed_mutation() on KillChainCapsule to:
        - Lower target_confirmation_threshold for faster lock on this threat type
        - Increase f2t2ea_phase_speed for quicker phase transitions
        
        This is the core of active evolution - changes happen mid-battle!
        """
        patterns = []
        
        # REAL-TIME pattern detection during Orient phase
        # This happens MID-BATTLE, not between games!
        detected_patterns = self.pattern_recognizer.detect_patterns_in_contacts(threatening_contacts)
        
        for pattern in detected_patterns:
            patterns.append(pattern)
            
            # ACTIVE EVOLUTION: >80% confidence triggers immediate mutation!
            if pattern.confidence > 0.8:
                logger.info(
                    f"🎯 PATTERN DETECTED ({pattern.confidence:.0%} confidence): "
                    f"{pattern.description} in {pattern.domain} domain"
                )
                
                # Immediately mutate the kill chain capsule
                mutation_applied = self.active_evolution.process_pattern(
                    pattern=pattern,
                    tick=tick,
                    threatening_contacts=threatening_contacts,
                )
                
                if mutation_applied:
                    self._mutations_performed += 1
                    logger.info(
                        f"⚡ BRAIN PHYSICALLY MUTATED: "
                        f"target_confirmation_threshold and f2t2ea_phase_speed "
                        f"adapted for {pattern.domain} threat"
                    )
        
        return patterns
    
    def directed_mutation(self, pattern: ThreatPattern) -> bool:
        """
        Directed mutation of KillChainCapsule based on enemy pattern.
        
        DEPRECATED: This method is kept for compatibility but the actual
        mutation logic now lives in ActiveEvolutionManager.process_pattern().
        
        If >80% confidence pattern detected:
        - Lower target_confirmation_threshold for faster lock
        - Increase f2t2ea_phase_speed for quicker response
        """
        # Delegate to the active evolution manager
        return self.active_evolution.process_pattern(
            pattern=pattern,
            tick=self._ooda_cycle,
            threatening_contacts=[],
        )
    
    def get_full_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        return {
            "config": self.config.to_dict(),
            "evolution": self.evolution_lab.get_stats(),
            "perception": self.situational_awareness.get_stats(),
            "tactical": self.tactical_engine.get_stats(),
            "strategy": {
                "doctrine": self.doctrine.get_stats(),
                "operational": self.operational_planner.get_stats(),
            },
            "comms": self.message_bus.get_stats(),
            "ooda": {
                "cycles": self._ooda_cycle,
                "mutations_performed": self._mutations_performed,
                "active_capabilities": self._get_active_capabilities(),
            },
        }
    
    def generative_loop(self, tick: int) -> Optional[Dict]:
        """
        Generative AI loop - runs every 50 ticks.
        """
        self._generative_tick += 1
        
        if self._generative_tick % 50 != 0:
            return None
        
        telemetry_stats = self.evolution_lab.telemetry.get_stats()
        weaknesses = self.adversarial_emulator.analyze_weaknesses(telemetry_stats)
        
        if not weaknesses:
            return None
        
        scenario = self.scenario_generator.generate(weaknesses, difficulty=0.7)
        
        if self.evolution_lab.genome_engine.active_genome:
            test_result = self.scenario_generator.fast_forward_test(
                None, self.evolution_lab.genome_engine.active_genome, ticks=50
            )
        
        tactics = self.tactical_synthesizer.synthesize()
        
        return {
            "weaknesses_found": weaknesses,
            "ghost_scenario": scenario.name,
            "tactics_generated": len(tactics),
        }
    
    def get_evolution_summary(self) -> str:
        return self.evolution_lab.get_evolution_summary()