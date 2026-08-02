# ULTRONE Programming Language Policy

## Overview

ULTRONE shall be implemented using a hybrid architecture that selects the most
appropriate language for each subsystem. This mirrors the way many state-of-the-art
AI organizations structure their engineering stacks.

## Python (Primary Language)

Python is the default language for:

- Reinforcement Learning
- Deep Learning
- Transformers
- Diffusion Models
- Large Language Models
- Multi-Agent Systems
- Knowledge Graphs
- Vector Databases
- Retrieval-Augmented Generation (RAG)
- Bayesian Optimization
- Evolutionary Algorithms
- Research Pipelines
- Experiment Management
- Data Processing
- Simulation Logic
- FastAPI Services
- Scientific Computing
- Autonomous Agents
- Training Pipelines

### Preferred Libraries

- PyTorch, JAX, TensorFlow
- NumPy, SciPy, scikit-learn
- Ray, Stable-Baselines3
- Hugging Face Transformers, Datasets
- PyTorch Geometric
- FAISS, ChromaDB, Qdrant
- NetworkX, Pandas, Polars
- OpenCV

## C++ / CUDA

Use C++ and CUDA when high performance is required.

### Target Modules

- GPU kernels
- Physics simulation
- Battlefield simulation
- Parallel pathfinding
- High-speed inference
- Custom tensor operations
- CUDA extensions
- Memory optimization
- Massive parallel processing

### Bindings

Expose C++/CUDA modules to Python using **pybind11**.

## Rust

Rust should be used for:

- Plugin runtime
- Secure networking
- Distributed communication
- Memory-safe services
- High-performance storage
- Asynchronous execution
- Event streaming
- Message queues

## Go

Go should power:

- Cluster management
- Distributed workers
- Scheduling
- Load balancing
- Container orchestration
- Monitoring
- Service discovery

## TypeScript

TypeScript should be used for:

- React dashboard
- Visualization
- Tactical map
- Experiment browser
- Live telemetry
- Research explorer
- Knowledge graph viewer
- Agent monitoring
- Admin console

## Code Generation Policy

When generating new modules:

1. Choose the language that best fits the subsystem.
2. Prefer Python unless another language provides significant advantages.
3. Use C++/CUDA only for computational bottlenecks.
4. Use Rust for memory safety and infrastructure.
5. Keep interfaces language-agnostic through APIs or bindings.
6. Preserve modularity and interoperability.

## Research Policy

ULTRONE should continuously study advances in:

- Artificial Intelligence, Machine Learning, Reinforcement Learning
- Multi-Agent Systems, Robotics, Distributed Systems
- Scientific Computing, Optimization, Knowledge Graphs
- Foundation Models, Computer Vision, Speech Processing
- Natural Language Processing, Autonomous Systems
- Explainable AI, Continual Learning, Meta-Learning

For every relevant paper or implementation, the system should:

1. Summarize the contribution
2. Extract algorithms and equations
3. Identify implementation details
4. Compare against existing approaches
5. Propose experiments for the simulation environment
6. Benchmark candidate improvements
7. Generate implementation plans
8. Record results with citations and provenance

Improvements should be developed in isolated branches or experimental modules,
thoroughly tested and benchmarked, and only recommended for integration after
meeting predefined quality criteria. Every experiment, result, and decision should
be logged to preserve a complete audit trail.