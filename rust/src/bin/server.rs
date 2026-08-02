// ULTRONE Plugin Runtime Server — async event streaming server
use ultrone_plugin_runtime::{PluginRuntime, Event, PluginInfo};
use std::time::{SystemTime, UNIX_EPOCH};

#[tokio::main]
async fn main() {
    println!("ULTRONE Plugin Runtime Server starting...");

    let runtime = PluginRuntime::new();

    // Register a test plugin
    let plugin = PluginInfo {
        plugin_id: "test-001".to_string(),
        name: "Test Plugin".to_string(),
        version: "1.0.0".to_string(),
        plugin_type: "algorithm".to_string(),
        description: "Test plugin for verification".to_string(),
        active: true,
    };
    runtime.register_plugin(plugin).await.unwrap();

    // Publish a test event
    let event = Event {
        event_id: "EVT-001".to_string(),
        event_type: "startup".to_string(),
        source: "server".to_string(),
        payload: serde_json::json!({"message": "Server started"}),
        timestamp: SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs(),
    };
    runtime.publish_event(event).await.unwrap();

    // Print stats
    let stats = runtime.get_stats().await;
    println!("Server stats: {}", serde_json::to_string_pretty(&stats).unwrap());

    println!("ULTRONE Plugin Runtime Server ready on port 9090");
    println!("Press Ctrl+C to stop");

    // Keep running
    tokio::signal::ctrl_c().await.ok();
    println!("Server shutting down...");
}