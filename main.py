#!/usr/bin/env python3
"""
Ultrone Battlefield AI Simulation
=================================
Living, evolving warfighting brain with generative AI capabilities.
"""

import asyncio
import logging
import random
from typing import Dict, Any

from brain import Orchestrator
from config import MilitaryConfig
from sim import WorldState, SimulationClock, AccelerationFactor
from data import Unit, DomainType
from agents import DroneAgent, FighterAgent
from generative import ReportGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (Ultrone): %(message)s"
)
logger = logging.getLogger("Ultrone.Main")


def create_initial_units() -> list:
    """Create initial blue forces."""
    units = []
    
    # Blue forces - air
    for i in range(2):
        units.append(DroneAgent(
            unit_id=f"BLUE-DRONE-{i:02d}",
            position=(random.uniform(1000, 5000), random.uniform(1000, 5000), 3000.0),
            team="blue"
        ).unit)
    
    # Blue forces - fighters
    for i in range(1):
        units.append(FighterAgent(
            unit_id=f"BLUE-FIGHTER-{i:02d}",
            position=(random.uniform(2000, 4000), random.uniform(2000, 4000), 8000.0),
            team="blue"
        ).unit)
    
    return units


def create_red_maneuver(tick: int) -> list:
    """Create surprise enemy maneuvers at specific ticks."""
    units = []
    
    # Tick 100-300: Enemy executes surprise maneuver
    if 100 <= tick <= 150:
        units.append(Unit(
            unit_id=f"RED-SURPRISE-{tick:03d}",
            domain=DomainType.AIR,
            unit_type="fighter_jet",
            position=(random.uniform(6000, 9000), random.uniform(6000, 9000), 8000.0),
            team="red",
            threat_level=10,
        ))
    
    # Tick 250-300: Multi-domain assault
    if 250 <= tick <= 300:
        units.extend([
            Unit(unit_id=f"RED-CYBER-{tick}", domain=DomainType.CYBER, unit_type="cyber",
                 position=(0,0,0), team="red", threat_level=8),
            Unit(unit_id=f"RED-SUB-{tick}", domain=DomainType.SEA, unit_type="submarine",
                 position=(7000, 7000, -100), team="red", threat_level=9),
        ])
    
    return units


async def run_simulation(config: MilitaryConfig, max_ticks: int = 500) -> None:
    """Run the evolving battlefield simulation."""
    logger.info("🎮 Ultrone Battlefield AI initializing...")
    
    # Initialize systems
    world = WorldState()
    clock = SimulationClock(tick_duration_seconds=0.5, acceleration=AccelerationFactor.FAST_10X)
    orchestrator = Orchestrator(config)
    report_gen = ReportGenerator()
    await orchestrator.initialize()
    
    # Create initial units
    for unit in create_initial_units():
        world.add_unit(unit)
    
    logger.info(f"Initialized with {len(world.units)} blue units")
    
    # Track battle progress
    battle_stats = {"total_engagements": 0, "successes": 0, "failures": 0}
    
    # Main loop - Phases 1-5
    tick = 0
    while tick < max_ticks:
        tick += 1
        clock.tick()
        
        # Phase 3: Surprise maneuver (100-300)
        if 100 <= tick <= 300:
            surprise_forces = create_red_maneuver(tick)
            for unit in surprise_forces:
                world.add_unit(unit)
            if surprise_forces:
                logger.warning(f"⚠️ SURPRISE ENEMY MANEUVER at tick {tick}!")
        
        # Process tick
        result = await orchestrator.process_tick(world, tick)
        
        # Phase 4: Generative loop (every 50 ticks after tick 200)
        if tick > 200 and tick % 50 == 0:
            gen_result = orchestrator.generative_loop(tick)
            if gen_result and gen_result.get("weaknesses_found"):
                logger.info(f"🧬 Generative AI active: Weaknesses={gen_result['weaknesses_found']}")
        
        battle_stats["total_engagements"] += result.get("orders_executed", 0)
        
        # Log every 25 ticks
        if tick % 25 == 0:
            logger.info(
                f"Tick {tick}: Threats={result['threats_detected']}, "
                f"Assessments={result['assessments']}, "
                f"Executed={result['orders_executed']}"
            )
        
        await asyncio.sleep(0.02)  # Fast simulation
    
    # Phase 5: Final AAR
    logger.info("\n" + "=" * 60)
    logger.info("GENERATING FINAL AAR...")
    
    stats = orchestrator.get_full_stats()
    aar = report_gen.generate_aar(
        battle_stats={
            "total_engagements": battle_stats["total_engagements"],
            "success_rate": 0.75,  # Simulated
            "avg_response_ms": 2500,
        },
        evolution_stats={
            "evolution_count": stats["evolution"]["lab"]["evolution_count"],
            "generation": stats["evolution"]["genome_engine"]["generation"],
            "best_fitness": stats["evolution"]["genome_engine"]["best_fitness"],
            "failure_analysis": stats["evolution"]["telemetry"].get("failure_analysis", {}),
        },
        tactics_used=["air_intercept", "multi_domain_strike"],
    )
    
    logger.info(aar.content)
    logger.info(f"\nSimulation complete: {stats['evolution']['lab']['evolution_count']} evolution cycles")


def main() -> None:
    """Entry point."""
    config = MilitaryConfig(max_ticks=500, evolution_enabled=True)
    asyncio.run(run_simulation(config))


if __name__ == "__main__":
    main()