#!/usr/bin/env python3
"""
Ultrone Battlefield AI Simulation
=================================

Autonomous, self-evolving warfighting brain with multi-session memory.
"""

import logging

from brain.orchestrator import Orchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (Ultrone): %(message)s"
)
logger = logging.getLogger("Ultrone.Main")

# Set to False for headless/server environments
USE_VISUALIZATION = True


def main() -> None:
    """Entry point - run autonomous training orchestrator."""
    logger.info("=" * 70)
    logger.info("ULTRONE AUTONOMOUS TRAINING SYSTEM")
    logger.info("=" * 70)
    
    # Initialize live telemetry dashboard if enabled
    dashboard = None
    if USE_VISUALIZATION:
        try:
            from viz.telemetry_dashboard import get_dashboard
            dashboard = get_dashboard(max_points=200)
            logger.info("Live telemetry dashboard initialized.")
        except Exception as e:
            logger.warning(f"Visualization disabled: {e}")
    
    # Create and run the orchestrator
    orchestrator = Orchestrator(
        num_episodes=100,
        max_steps_per_episode=200,
        initial_mutation_rate=0.15,
    )
    
    summary = orchestrator.run()
    
    # Final report
    logger.info("\n" + "=" * 70)
    logger.info("TRAINING COMPLETE - FINAL SUMMARY")
    logger.info("=" * 70)
    logger.info(f"  Total Episodes     : {summary.get('total_episodes', 0)}")
    logger.info(f"  Overall Success    : {summary.get('success_rate', 0.0):.1%}")
    logger.info(f"  Average Reward     : {summary.get('avg_reward', 0.0):.1f}")
    logger.info(f"  Best Fitness       : {summary.get('best_fitness', 0.0):.3f}")
    logger.info(f"  Final Mutation Rate: {summary.get('final_mutation_rate', 0.0):.4f}")
    logger.info(f"  Final Generation   : {summary.get('generation', 0)}")
    logger.info("=" * 70)
    
    # Keep window open after training if visualization was enabled
    if dashboard is not None:
        try:
            import matplotlib.pyplot as plt
            logger.info("Close the matplotlib window to exit.")
            plt.ioff()
            plt.show()
        except Exception:
            pass


if __name__ == "__main__":
    main()