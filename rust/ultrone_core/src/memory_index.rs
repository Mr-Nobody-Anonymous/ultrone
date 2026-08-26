// Inverted memory index: token -> document ids.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use std::collections::{HashMap, HashSet};

fn tokenize(text: &str) -> Vec<String> {
    text.split_whitespace()
        .map(|word| {
            word.trim_matches(|c: char|
                ".,;:!?)(".contains(c)).to_lowercase()
        })
        .filter(|token| !token.is_empty())
        .collect()
}

#[pyclass]
pub struct MemoryIndex {
    index: HashMap<String, HashSet<String>>,
    docs: HashMap<String, String>,
}

#[pymethods]
impl MemoryIndex {
    #[new]
    fn new() -> Self {
        Self { index: HashMap::new(), docs: HashMap::new() }
    }

    /// Index a document; returns the number of tokens stored.
    fn index_document(&mut self, doc_id: String, text: String)
                      -> PyResult<usize> {
        if self.docs.contains_key(&doc_id) {
            return Err(PyValueError::new_err(format!(
                "document '{}' already indexed", doc_id)));
        }
        let tokens = tokenize(&text);
        for token in &tokens {
            self.index
                .entry(token.clone())
                .or_default()
                .insert(doc_id.clone());
        }
        self.docs.insert(doc_id, text);
        Ok(tokens.len())
    }

    fn search(&self, term: String) -> Vec<String> {
        let term = term.to_lowercase();
        let mut ids: Vec<String> = self
            .index
            .get(&term)
            .map(|set| set.iter().cloned().collect())
            .unwrap_or_default();
        ids.sort();
        ids
    }

    fn remove_document(&mut self, doc_id: String) -> bool {
        match self.docs.remove(&doc_id) {
            Some(text) => {
                for token in tokenize(&text) {
                    if let Some(bucket) = self.index.get_mut(&token) {
                        bucket.remove(&doc_id);
                        if bucket.is_empty() {
                            self.index.remove(&token);
                        }
                    }
                }
                true
            }
            None => false,
        }
    }

    fn stats(&self) -> (usize, usize) {
        (self.docs.len(), self.index.len())
    }
}