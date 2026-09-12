// World state: entity store + fixed-step integration.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use std::collections::HashMap;

#[pyclass]
pub struct WorldState {
    entities: HashMap<String, [f64; 4]>,   // x, y, vx, vy
    kinds: HashMap<String, String>,
    tick: u64,
}

#[pymethods]
impl WorldState {
    #[new]
    fn new() -> Self {
        Self {
            entities: HashMap::new(),
            kinds: HashMap::new(),
            tick: 0,
        }
    }

    fn spawn(&mut self, entity_id: String, x: f64, y: f64,
             vx: f64, vy: f64, kind: String) -> PyResult<()> {
        if self.entities.contains_key(&entity_id) {
            return Err(PyValueError::new_err(format!(
                "entity '{}' already exists", entity_id)));
        }
        self.entities.insert(entity_id.clone(), [x, y, vx, vy]);
        self.kinds.insert(entity_id, kind);
        Ok(())
    }

    fn update_velocity(&mut self, entity_id: String,
                       vx: f64, vy: f64) -> bool {
        match self.entities.get_mut(&entity_id) {
            Some(state) => {
                state[2] = vx;
                state[3] = vy;
                true
            }
            None => false,
        }
    }

    /// (x, y, vx, vy, kind) or None.
    fn get(&self, entity_id: String)
           -> Option<(f64, f64, f64, f64, String)> {
        let state = self.entities.get(&entity_id)?;
        Some((state[0], state[1], state[2], state[3],
              self.kinds.get(&entity_id)?.clone()))
    }

    /// Integrate one fixed tick; returns the new tick counter.
    fn step(&mut self, dt: f64) -> u64 {
        self.tick += 1;
        for state in self.entities.values_mut() {
            state[0] += state[2] * dt;
            state[1] += state[3] * dt;
        }
        self.tick
    }

    fn count(&self) -> usize {
        self.entities.len()
    }

    fn tick(&self) -> u64 {
        self.tick
    }

    /// Deterministic snapshot: (tick, sorted rows of
    /// (id, x, y, vx, vy)).
    fn snapshot(&self) -> (u64, Vec<(String, f64, f64, f64, f64)>) {
        let mut rows: Vec<(String, f64, f64, f64, f64)> = self
            .entities
            .iter()
            .map(|(id, s)| (id.clone(), s[0], s[1], s[2], s[3]))
            .collect();
        rows.sort_by(|a, b| a.0.cmp(&b.0));
        (self.tick, rows)
    }
}