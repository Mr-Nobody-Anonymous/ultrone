# Phase 7: Generative + Evolutionary AI Upgrades

## Implementation Checklist

### [x] 1. LLMCommander — Chain-of-Thought + Self-Correction
   - [x] Plan approved
   - [x] Implement `_chain_of_thought()` with 4-step reasoning pipeline
   - [x] Implement `_self_correct()` with critique + MC/KG validation
   - [x] Enhance `_rule_based_analysis()` to emit CoT + corrected output

### [x] 2. MonteCarloEngine — UCT Selection Strategy
   - [x] Plan approved
   - [x] Add UCT tracking structures (visit_counts, reward_sums)
   - [x] Replace random friction with UCT-biased fork configuration
   - [x] Maintain 5% random exploration floor

### [x] 3. CoevolutionEngine — AlphaStar League Training
   - [x] Plan approved
   - [x] Add league population managers (main, exploiters, past_selves)
   - [x] Implement SBX crossover and polynomial mutation
   - [x] Implement self-adaptive mutation rate with [0.01, 0.30] bounds
   - [x] Implement league-based fitness evaluation

### [ ] 4. Validation
   - [ ] Run `test_phase6_palantir.py` — all tests pass
   - [ ] Run `stress_test_red_queen.py` — no regressions

