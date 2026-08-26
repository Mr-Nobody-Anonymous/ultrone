// Deterministic tick-ordered scheduler (min-heap on tick, then id).
// Payloads live caller-side (Python); the kernel orders and filters.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use std::cmp::Reverse;
use std::collections::{BinaryHeap, HashSet};

#[pyclass]
pub struct TickScheduler {
    heap: BinaryHeap<Reverse<(u64, String)>>,
    pending_ids: HashSet<String>,
    cancelled: HashSet<String>,
}

#[pymethods]
impl TickScheduler {
    #[new]
    fn new() -> Self {
        Self {
            heap: BinaryHeap::new(),
            pending_ids: HashSet::new(),
            cancelled: HashSet::new(),
        }
    }

    fn schedule(&mut self, tick: u64, task_id: String) -> PyResult<()> {
        if self.pending_ids.contains(&task_id) {
            return Err(PyValueError::new_err(format!(
                "task '{}' already scheduled", task_id)));
        }
        self.heap.push(Reverse((tick, task_id.clone())));
        self.pending_ids.insert(task_id);
        Ok(())
    }

    fn cancel(&mut self, task_id: String) -> bool {
        if self.pending_ids.remove(&task_id) {
            self.cancelled.insert(task_id);
            true
        } else {
            false
        }
    }

    /// Pop every task with tick <= now_tick, ordered by (tick, id).
    /// Returns Vec<(tick, task_id)>; payloads are attached by the caller.
    fn pop_due(&mut self, now_tick: u64)
               -> Vec<(u64, String)> {
        let mut due: Vec<(u64, String)> = Vec::new();
        while let Some(Reverse((tick, id))) = self.heap.peek().copied() {
            if tick > now_tick {
                break;
            }
            self.heap.pop();
            if self.cancelled.remove(&id) {
                continue;
            }
            self.pending_ids.remove(&id);
            due.push((tick, id));
        }
        due
    }

    fn pending(&self) -> usize {
        self.pending_ids.len()
    }
}