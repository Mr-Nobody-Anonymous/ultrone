// Command route table + bounded audit log.
// Validation/routing only: execution stays on the caller's command path.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use std::collections::{HashMap, HashSet};

const MAX_LOG: usize = 256;

#[pyclass]
pub struct CommandRouter {
    routes: HashMap<String, HashSet<String>>,
    log: Vec<(String, String, bool)>,   // target, action, accepted
}

#[pymethods]
impl CommandRouter {
    #[new]
    fn new() -> Self {
        Self { routes: HashMap::new(), log: Vec::new() }
    }

    fn register(&mut self, target: String, action: String) -> PyResult<bool> {
        let actions = self.routes.entry(target.clone()).or_default();
        if !actions.insert(action.clone()) {
            return Err(PyValueError::new_err(format!(
                "route {}.{} already registered", target, action)));
        }
        Ok(true)
    }

    /// Accept/reject a routing request and record it in the audit log.
    fn route(&mut self, target: String, action: String) -> bool {
        let known = self
            .routes
            .get(&target)
            .map(|actions| actions.contains(&action))
            .unwrap_or(false);
        self.log.push((target, action, known));
        if self.log.len() > MAX_LOG {
            self.log.remove(0);
        }
        known
    }

    fn routes_for(&self, target: String) -> Vec<String> {
        let mut actions: Vec<String> = self
            .routes
            .get(&target)
            .map(|actions| actions.iter().cloned().collect())
            .unwrap_or_default();
        actions.sort();
        actions
    }

    fn log_tail(&self, n: usize) -> Vec<(String, String, bool)> {
        let start = self.log.len().saturating_sub(n);
        self.log[start..].to_vec()
    }
}