// ULTRONE Core Runtime -- deterministic high-performance kernels.
//
// One class per concern, mirroring the pure-Python references in
// `ultrone_rt/kernels.py`: identical names, arguments, and results, so
// `ultrone_rt.loader` can swap backends transparently.
//
// Build:  cd rust/ultrone_core && maturin develop   (or pip wheel .)

mod command_bus;
mod evaluation;
mod memory_index;
mod simulation;
mod scheduler;
mod spatial;
mod tensor_ops;
mod world_state;

use pyo3::prelude::*;
use pyo3::types::PyModule;

/// Backend marker returned to `ultrone_rt.loader`.
#[pyfunction]
fn backend_name() -> &'static str {
    "rust"
}

#[pymodule]
fn ultrone_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<world_state::WorldState>()?;
    m.add_class::<simulation::Simulator>()?;
    m.add_class::<spatial::SpatialIndex>()?;
    m.add_class::<scheduler::TickScheduler>()?;
    m.add_class::<command_bus::CommandRouter>()?;
    m.add_class::<memory_index::MemoryIndex>()?;
    m.add_function(wrap_pyfunction!(tensor_ops::dot_product, m)?)?;
    m.add_function(wrap_pyfunction!(tensor_ops::cosine_similarity, m)?)?;
    m.add_function(wrap_pyfunction!(tensor_ops::softmax, m)?)?;
    m.add_function(wrap_pyfunction!(tensor_ops::top_k_indices, m)?)?;
    m.add_function(wrap_pyfunction!(
        evaluation::batch_sphere_eval, m)?)?;
    m.add_function(wrap_pyfunction!(backend_name, m)?)?;
    m.add("__version__", "0.1.0")?;
    Ok(())
}