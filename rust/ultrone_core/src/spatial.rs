// Uniform-grid spatial index for radius queries.

use pyo3::prelude::*;
use std::collections::HashMap;

type CellKey = (i64, i64);

#[pyclass]
pub struct SpatialIndex {
    cell_size: f64,
    grid: HashMap<CellKey, Vec<(String, f64, f64)>>,
    total: usize,
}

fn cell_of(x: f64, y: f64, cell_size: f64) -> CellKey {
    ((x / cell_size).floor() as i64, (y / cell_size).floor() as i64)
}

#[pymethods]
impl SpatialIndex {
    #[new]
    fn new(cell_size: Option<f64>) -> Self {
        Self {
            cell_size: cell_size.unwrap_or(1.0).max(1e-9),
            grid: HashMap::new(),
            total: 0,
        }
    }

    fn insert(&mut self, point_id: String, x: f64, y: f64) {
        let key = cell_of(x, y, self.cell_size);
        self.grid.entry(key).or_default().push((point_id, x, y));
        self.total += 1;
    }

    /// Ids within `radius` of (x, y), nearest first.
    fn query_radius(&self, x: f64, y: f64, radius: f64) -> Vec<String> {
        let reach = (radius / self.cell_size).ceil() as i64;
        let center = cell_of(x, y, self.cell_size);
        let r_sq = radius * radius;
        let mut hits: Vec<(f64, String)> = Vec::new();
        for gx in (center.0 - reach)..=(center.0 + reach) {
            for gy in (center.1 - reach)..=(center.1 + reach) {
                if let Some(bucket) = self.grid.get(&(gx, gy)) {
                    for (point_id, px, py) in bucket {
                        let d_sq =
                            (px - x) * (px - x) + (py - y) * (py - y);
                        if d_sq <= r_sq {
                            hits.push((d_sq, point_id.clone()));
                        }
                    }
                }
            }
        }
        hits.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap());
        hits.into_iter().map(|(_, id)| id).collect()
    }

    fn __len__(&self) -> usize {
        self.total
    }
}