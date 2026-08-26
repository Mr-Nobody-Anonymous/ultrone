// Batch evaluation kernels for the adaptive layer's populations.

use pyo3::prelude::*;

/// Deterministic sphere benchmark: sum of squares per individual,
/// rounded to 6 decimals -- byte-identical to the Python reference.
#[pyfunction]
pub fn batch_sphere_eval(population: Vec<Vec<f64>>) -> Vec<f64> {
    population
        .iter()
        .map(|individual| {
            let sum: f64 = individual.iter().map(|x| x * x).sum();
            (sum * 1_000_000.0).round() / 1_000_000.0
        })
        .collect()
}