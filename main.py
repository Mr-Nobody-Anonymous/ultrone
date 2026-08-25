#!/usr/bin/env python3
"""
Ultrone Battlefield AI Simulation
=================================

Autonomous, self-evolving warfighting brain with multi-session memory.
"""

import argparse
import logging
import sys
from typing import List

from brain.orchestrator import Orchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (Ultrone): %(message)s"
)
logger = logging.getLogger("Ultrone.Main")

# Set to False for headless/server environments
USE_VISUALIZATION = True


def main(argv: List[str] | None = None) -> None:
    """Entry point - run autonomous training orchestrator or benchmark hardware."""
    parser = argparse.ArgumentParser(description="Ultrone CLI")
    parser.add_argument("command", nargs="?", default="train", choices=["train", "benchmark"], help="Command to run")
    parser.add_argument("--benchmark", default="hardware", help="Benchmark target")
    parser.add_argument("--profile", default="auto",
                        choices=["auto", "ultra_fast", "balanced", "research", "max_quality"],
                        help="Performance profile")
    parser.add_argument("--device", default="auto",
                        choices=["auto", "cpu", "cuda", "mps", "rocm"],
                        help="Execution device")
    parser.add_argument("--precision", default="auto",
                        choices=["auto", "fp32", "fp16", "bf16", "int8"],
                        help="Precision mode")
    args = parser.parse_args(argv)

    # Apply performance profile via environment
    if args.profile != "auto":
        import os
        os.environ["ULTRONE_PERFORMANCE_PROFILE"] = args.profile
    if args.device != "auto":
        import os
        os.environ["ULTRONE_DEVICE"] = args.device
    if args.precision != "auto":
        import os
        os.environ["ULTRONE_PRECISION"] = args.precision

    if args.command == "benchmark":
        from runtime import benchmark_hardware

        report = benchmark_hardware()
        logger.info("=" * 70)
        logger.info("ULTRONE HARDWARE REPORT")
        logger.info("=" * 70)
        logger.info(f"Device: {report['device']}")
        logger.info(f"Backend: {report['backend']}")
        logger.info(f"Precision: {report['precision']}")
        logger.info(f"Backend description: {report.get('backend_description', 'N/A')}")
        logger.info(f"CPU count: {report.get('cpu_count', 'N/A')}")
        logger.info(f"RAM: {report.get('ram_bytes', 0) / (1024**3):.1f} GB")
        logger.info(f"Matmul latency: {report.get('matmul_latency_ms', 0):.3f} ms")
        logger.info(f"Inference latency: {report['latency_seconds']:.6f}s")
        logger.info(f"Cached models: {report['cached_models']}")
        logger.info("=" * 70)
        return

    logger.info("=" * 70)
    logger.info("ULTRONE AUTONOMOUS TRAINING SYSTEM")
    logger.info("=" * 70)

    dashboard = None
    if USE_VISUALIZATION:
        try:
            from viz.telemetry_dashboard import get_dashboard
            dashboard = get_dashboard(max_points=200)
            logger.info("Live telemetry dashboard initialized.")
        except Exception as e:
            logger.warning(f"Visualization disabled: {e}")

    orchestrator = Orchestrator(
        num_episodes=100,
        max_steps_per_episode=200,
        initial_mutation_rate=0.15,
    )

    summary = orchestrator.run()

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