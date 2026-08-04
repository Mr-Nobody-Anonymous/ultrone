# Situational Awareness System

State-of-the-art situational awareness for the UltronE research platform,
inspired by Endsley's three-level model, the JDL Data Fusion Model, the OODA
Loop, probabilistic robotics, and modern deep learning research.

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                            SITUATIONAL AWARENESS ENGINE                              │
│                                                                                      │
│  ┌─────────────── LEVEL 1: PERCEPTION ───────────────┐                               │
│  │                                                   │                               │
│  │  ┌──────────┐   ┌────────────┐   ┌────────────┐  │                               │
│  │  │ Sensors  │──▶│ Validator  │──▶│ Tracker    │  │                               │
│  │  │ Registry │   │            │   │            │  │                               │
│  │  └──────────┘   └────────────┘   └────────────┘  │                               │
│  │        │              │                │          │                               │
│  │        ▼              ▼                ▼          │                               │
│  │  ┌────────────────────────────────────────────┐  │                               │
│  │  │          Sensor Fusion Engine             │  │                               │
│  │  │  Bayesian │ EKF │ UKF │ Particle │ D-S    │  │                               │
│  │  │  Covariance Intersection │ Neural         │  │                               │
│  │  └────────────────────────────────────────────┘  │                               │
│  │              │                                    │                               │
│  │              ▼                                    │                               │
│  │  ┌────────────────────────────────────────────┐  │                               │
│  │  │          Belief State Estimator           │  │                               │
│  │  │  Gaussian │ Particle │ Categorical        │  │                               │
│  │  └────────────────────────────────────────────┘  │                               │
│  └───────────────────────────────────────────────────┘                               │
│                          │                                                            │
│                          ▼                                                            │
│  ┌─────────────── LEVEL 2: COMPREHENSION ─────────────┐                              │
│  │                                                    │                              │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐     │                              │
│  │  │ World    │  │ Scene    │  │ Semantic     │     │                              │
│  │  │ Model    │  │ Graph    │  │ Map          │     │                              │
│  │  └──────────┘  └──────────┘  └──────────────┘     │                              │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐     │                              │
│  │  │ Temporal │  │ Causal   │  │ Dynamic      │     │                              │
│  │  │ Reasoner │  │ Reasoner │  │ Map          │     │                              │
│  │  └──────────┘  └──────────┘  └──────────────┘     │                              │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐     │                              │
│  │  │ Threat   │  │ Anomaly  │  │ Intent       │     │                              │
│  │  │ Assessor │  │ Detector │  │ Estimator    │     │                              │
│  │  └──────────┘  └──────────┘  └──────────────┘     │                              │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐     │                              │
│  │  │ Context  │  │ Confidence│ │ Uncertainty  │     │                              │
│  │  │ Engine   │  │ Engine   │ │ Engine       │     │                              │
│  │  └──────────┘  └──────────┘  └──────────────┘     │                              │
│  └────────────────────────────────────────────────────┘                              │
│                          │                                                            │
│                          ▼                                                            │
│  ┌─────────────── LEVEL 3: PROJECTION ──────────────┐                               │
│  │                                                  │                               │
│  │  ┌─────────────────┐  ┌──────────────────┐      │                               │
│  │  │ Trajectory      │  │ Event            │      │                               │
│  │  │ Predictor       │  │ Predictor        │      │                               │
│  │  └─────────────────┘  └──────────────────┘      │                               │
│  │  ┌─────────────────┐  ┌──────────────────┐      │                               │
│  │  │ Uncertainty     │  │ Monte Carlo      │      │                               │
│  │  │ Propagation     │  │ Simulation       │      │                               │
│  │  └─────────────────┘  └──────────────────┘      │                               │
│  └──────────────────────────────────────────────────┘                               │
│                          │                                                            │
│                          ▼                                                            │
│  ┌─────────── CROSS-CUTTING CONCERNS ────────────┐                                  │
│  │                                               │                                  │
│  │  Attention Manager │ Active Perception       │                                  │
│  │  Object Memory     │ Hypothesis Manager      │                                  │
│  │  Explainability    │ Visualization           │                                  │
│  │  Event Bus         │ Performance Telemetry   │                                  │
│  └───────────────────────────────────────────────┘                                  │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

## Sequence Diagram (Perception Pipeline)

```
Sensor        Validator      Tracker       Fusion        Belief         WorldModel
  │              │              │            │              │              │
  │ observation  │              │            │              │              │
  │────────── ──▶│ validate     │            │              │              │
  │              │─────────────▶│            │              │              │
  │              │              │ associate   │              │              │
  │              │              │────────────▶│             │              │
  │              │              │             │ fuse         │              │
  │              │              │             │────────────▶│              │
  │              │              │             │              │ update       │
  │              │              │             │              │─────────────▶│
  │              │              │             │              │              │
  │              │              │             │              │  commit_tick │
  │              │              │             │              │◀─────────────│
```

## State Diagram (Entity Lifecycle)

```
         ┌──────────────┐
         │   UNKNOWN    │
         └──────┬───────┘
                │ first observation
                ▼
         ┌──────────────┐
         │  CANDIDATE   │
         └──────┬───────┘
                │ N observations (confirmation)
                ▼
         ┌──────────────┐
         │  CONFIRMED   │
         └──────┬───────┘
                │
       ┌────────┼────────┐
       ▼        ▼        ▼
  ┌────────┐ ┌────────┐ ┌────────┐
  │CLASS-  │ │RE-     │ │PREDICT-│
  │IFIED   │ │LATION  │ │ED      │
  └────────┘ └────────┘ └────────┘
       │
       │ stale / not observed
       ▼
  ┌──────────────┐
  │   STALE      │
  └──────┬───────┘
         │ pruned
         ▼
  ┌──────────────┐
  │   REMOVED    │
  └──────────────┘
```

## Class Diagram (Core Subsystems)

```
┌─────────────────────┐     ┌─────────────────────┐
│    AwarenessEngine  │     │     EventBus        │
├─────────────────────┤     ├─────────────────────┤
│ - world_model       │────▶│ + subscribe()       │
│ - sensor_fusion     │     │ + publish()         │
│ - scene_graph       │     │ + publish_sync()    │
│ - threat_assessor   │     └─────────────────────┘
│ - trajectory_predict│
│ - explainability    │     ┌─────────────────────┐
└─────────────────────┘     │     WorldModel      │
                            ├─────────────────────┤
┌─────────────────────┐     │ + create_entity()   │
│  SensorFusionEngine │     │ + update_entity()   │
├─────────────────────┤     │ + add_relationship()│
│ + fuse()            │     │ + snapshot()        │
│ + fuse_by_entity()  │     └─────────────────────┘
└─────────────────────┘
                            ┌─────────────────────┐
┌─────────────────────┐     │    SensorRegistry   │
│ BeliefStateEstimator│     ├─────────────────────┤
├─────────────────────┤     │ + register()        │
│ + gaussian_update() │     │ + update_quality()  │
│ + particle_update() │     │ + by_type()         │
│ + categorical_update│     └─────────────────────┘
└─────────────────────┘
```

## Module Reference

### Level 1: Perception
| Module | Responsibility |
|--------|---------------|
| `sensor_registry.py` | Sensor registration, quality metrics, adapter protocol |
| `observation_validation.py` | Schema, timestamp, confidence, covariance validation |
| `entity_tracker.py` | Observation-to-entity association, track lifecycle |
| `sensor_fusion.py` | Bayesian, EKF, UKF, Particle, D-S, Covariance Intersection, Neural fusion |
| `belief_state.py` | Recursive Bayesian belief estimation |
| `observation_history.py` | Bounded per-entity/per-sensor observation history |

### Level 2: Comprehension
| Module | Responsibility |
|--------|---------------|
| `world_model.py` | Digital twin: entities, relationships, observations, snapshots |
| `scene_graph.py` | Spatial-semantic graph with queries and statistics |
| `semantic_mapper.py` | Semantic regions with labels and categories |
| `dynamic_map.py` | Occupancy grid with decay and semantic layers |
| `temporal_reasoner.py` | Trends, periodicity, anomalies, cross-correlation |
| `causal_reasoner.py` | Causal link inference and counterfactual reasoning |
| `threat_assessor.py` | Multi-factor threat scoring |
| `anomaly_detector.py` | Z-score and jump-based anomaly detection |
| `intent_estimator.py` | Behavioral intent classification |
| `context_engine.py` | Environmental and situational context assembly |
| `confidence_engine.py` | Confidence aggregation, decay, calibration |
| `uncertainty_engine.py` | Uncertainty metrics and propagation |
| `uncertainty_propagation.py` | End-to-end uncertainty tracing |
| `change_detector.py` | Appearance, movement, attribute, classification changes |
| `hypothesis_manager.py` | Competing hypothesis lifecycle and evidence |
| `object_memory.py` | Long-term object knowledge with decay |

### Level 3: Projection
| Module | Responsibility |
|--------|---------------|
| `trajectory_predictor.py` | Kinematic and Monte Carlo trajectory prediction |
| `event_predictor.py` | Rule-based event forecasting |
| `uncertainty_propagation.py` | Prediction uncertainty growth |

### Attention and Active Perception
| Module | Responsibility |
|--------|---------------|
| `attention_manager.py` | Dynamic attention allocation, novelty, saliency |
| `information_gain.py` | Entropy reduction estimation for sensor selection |
| `active_perception.py` | Curiosity-driven sensing action recommendation |

### Explainability and Visualization
| Module | Responsibility |
|--------|---------------|
| `explainability.py` | Evidence chains, probability explanations, alternatives |
| `visualization.py` | World state serialization and situational summaries |

## Research Interface Points

The system provides clean extension points for research:

- **Continual Learning**: `ObjectMemory.consolidate()` for memory consolidation
- **Meta Learning**: `ConfidenceEngine.learn_calibration()` for calibration
- **Domain Adaptation**: `SensorRegistry` for sensor-specific adaptation
- **Transfer Learning**: `NeuralFusion` pluggable model interface
- **Graph Representation Learning**: `SceneGraph` for GNN input
- **Reinforcement Learning**: `AttentionManager` for reward-driven sensing
- **Foundation Models**: `SensorAdapter` protocol for adapter integration
- **Self-supervised Learning**: `ObservationHistory` for contrastive pre-training

## Performance

Benchmarks (Python 3.10, Windows 11, single-threaded):

| Operation | Latency |
|-----------|---------|
| Full engine tick (10 entities) | ~4.4 ms |
| Sensor fusion (Bayesian) | ~0.37 ms |
| Trajectory prediction | ~0.28 ms |
| Entity creation | ~0.17 ms |
| Threat assessment | ~0.05 ms |
| Event prediction | ~0.05 ms |
| Attention allocation | ~0.03 ms |