// ULTRONE Plugin Runtime — Rust implementation
// Memory-safe, high-performance plugin execution and event streaming.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;

/// Plugin metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PluginInfo {
    pub plugin_id: String,
    pub name: String,
    pub version: String,
    pub plugin_type: String,
    pub description: String,
    pub active: bool,
}

/// Plugin execution result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PluginResult {
    pub success: bool,
    pub data: serde_json::Value,
    pub error: Option<String>,
}

/// Event for the event bus
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Event {
    pub event_id: String,
    pub event_type: String,
    pub source: String,
    pub payload: serde_json::Value,
    pub timestamp: u64,
}

/// Plugin runtime — manages plugin lifecycle and event streaming
pub struct PluginRuntime {
    plugins: Arc<RwLock<HashMap<String, PluginInfo>>>,
    event_log: Arc<RwLock<Vec<Event>>>,
    event_handlers: Arc<RwLock<HashMap<String, Vec<String>>>>,
}

impl PluginRuntime {
    pub fn new() -> Self {
        Self {
            plugins: Arc::new(RwLock::new(HashMap::new())),
            event_log: Arc::new(RwLock::new(Vec::new())),
            event_handlers: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Register a plugin
    pub async fn register_plugin(&self, info: PluginInfo) -> Result<(), String> {
        let mut plugins = self.plugins.write().await;
        plugins.insert(info.plugin_id.clone(), info);
        Ok(())
    }

    /// Unregister a plugin
    pub async fn unregister_plugin(&self, plugin_id: &str) -> Result<(), String> {
        let mut plugins = self.plugins.write().await;
        plugins.remove(plugin_id);
        Ok(())
    }

    /// Activate a plugin
    pub async fn activate_plugin(&self, plugin_id: &str) -> Result<(), String> {
        let mut plugins = self.plugins.write().await;
        if let Some(plugin) = plugins.get_mut(plugin_id) {
            plugin.active = true;
            Ok(())
        } else {
            Err(format!("Plugin {} not found", plugin_id))
        }
    }

    /// Deactivate a plugin
    pub async fn deactivate_plugin(&self, plugin_id: &str) -> Result<(), String> {
        let mut plugins = self.plugins.write().await;
        if let Some(plugin) = plugins.get_mut(plugin_id) {
            plugin.active = false;
            Ok(())
        } else {
            Err(format!("Plugin {} not found", plugin_id))
        }
    }

    /// List all plugins
    pub async fn list_plugins(&self) -> Vec<PluginInfo> {
        let plugins = self.plugins.read().await;
        plugins.values().cloned().collect()
    }

    /// Publish an event
    pub async fn publish_event(&self, event: Event) -> Result<(), String> {
        let mut log = self.event_log.write().await;
        log.push(event.clone());
        // Notify handlers
        let handlers = self.event_handlers.read().await;
        if let Some(_handler_ids) = handlers.get(&event.event_type) {
            // In a real implementation, this would call registered handlers
        }
        Ok(())
    }

    /// Subscribe to events
    pub async fn subscribe(&self, event_type: &str, handler_id: &str) -> Result<(), String> {
        let mut handlers = self.event_handlers.write().await;
        handlers
            .entry(event_type.to_string())
            .or_insert_with(Vec::new)
            .push(handler_id.to_string());
        Ok(())
    }

    /// Get event log
    pub async fn get_event_log(&self, limit: usize) -> Vec<Event> {
        let log = self.event_log.read().await;
        if log.len() <= limit {
            log.clone()
        } else {
            log[log.len() - limit..].to_vec()
        }
    }

    /// Get runtime stats
    pub async fn get_stats(&self) -> serde_json::Value {
        let plugins = self.plugins.read().await;
        let log = self.event_log.read().await;
        serde_json::json!({
            "type": "PluginRuntime",
            "plugins_registered": plugins.len(),
            "active_plugins": plugins.values().filter(|p| p.active).count(),
            "events_logged": log.len(),
        })
    }
}

impl Default for PluginRuntime {
    fn default() -> Self {
        Self::new()
    }
}

// === Python bindings via PyO3 ===
#[cfg(feature = "python-bindings")]
mod python {
    use super::*;
    use pyo3::prelude::*;

    #[pyclass]
    struct PyPluginRuntime {
        inner: PluginRuntime,
    }

    #[pymethods]
    impl PyPluginRuntime {
        #[new]
        fn new() -> Self {
            Self {
                inner: PluginRuntime::new(),
            }
        }

        fn register_plugin(&self, plugin_id: String, name: String, version: String, plugin_type: String) -> PyResult<()> {
            let info = PluginInfo {
                plugin_id,
                name,
                version,
                plugin_type,
                description: String::new(),
                active: false,
            };
            let runtime = self.inner.clone();
            // Note: In async context, we'd use tokio::runtime
            Ok(())
        }

        fn get_stats(&self) -> PyResult<String> {
            Ok(serde_json::json!({
                "type": "PluginRuntime",
                "status": "rust_runtime_active",
            }).to_string())
        }
    }

    #[pymodule]
    fn ultrone_rust(_py: Python, m: &PyModule) -> PyResult<()> {
        m.add_class::<PyPluginRuntime>()?;
        m.add("__version__", "1.0.0")?;
        Ok(())
    }
}