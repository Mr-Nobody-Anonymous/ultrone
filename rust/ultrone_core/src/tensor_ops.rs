// Tensor-style operations mirroring ultrone_bindings fallbacks.

use pyo3::prelude::*;

#[pyfunction]
pub fn dot_product(a: Vec<f64>, b: Vec<f64>) -> f64 {
    a.iter().zip(b.iter()).map(|(x, y)| x * y).sum()
}

#[pyfunction]
pub fn cosine_similarity(a: Vec<f64>, b: Vec<f64>) -> f64 {
    let dot = dot_product(a.clone(), b.clone());
    let norm_a = a.iter().map(|x| x * x).sum::<f64>().sqrt();
    let norm_b = b.iter().map(|x| x * x).sum::<f64>().sqrt();
    if norm_a == 0.0 || norm_b == 0.0 {
        return 0.0;
    }
    dot / (norm_a * norm_b)
}

#[pyfunction]
#[pyo3(signature = (scores, temperature=1.0))]
pub fn softmax(scores: Vec<f64>, temperature: f64) -> Vec<f64> {
    if scores.is_empty() {
        return scores;
    }
    let temp = temperature.max(1e-9);
    let peak = scores.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    let exps: Vec<f64> = scores
        .iter()
        .map(|v| ((v - peak) / temp).exp())
        .collect();
    let total: f64 = exps.iter().sum();
    exps.iter().map(|v| v / total).collect()
}

#[pyfunction]
pub fn top_k_indices(scores: Vec<f64>, k: usize) -> Vec<usize> {
    let mut order: Vec<usize> = (0..scores.len()).collect();
    order.sort_by(|&i, &j| {
        scores[j]
            .partial_cmp(&scores[i])
            .unwrap_or(std::cmp::Ordering::Equal)
            .then(i.cmp(&j))
    });
    order.truncate(k);
    order
}