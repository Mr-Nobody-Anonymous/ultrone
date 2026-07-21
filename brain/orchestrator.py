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