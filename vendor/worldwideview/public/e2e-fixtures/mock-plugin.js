// This file is loaded by the plugin manager in the E2E test environment.
// It bypasses the build step and directly uses the host's injected React instance.

export default {
    // Basic plugin metadata required by WorldPlugin interface
    id: "e2e-mock-plugin",
    name: "E2E Mock Plugin",
    description: "A mock plugin for E2E testing.",
    icon: "data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=", // Empty SVG as fallback
    category: "custom",
    version: "1.0.0",
    
    // Lifecycle
    initialize: async (ctx) => {
        console.log("[e2e-mock-plugin] Initialized");
    },
    destroy: () => {
        console.log("[e2e-mock-plugin] Destroyed");
    },

    // Data
    fetch: async (timeRange) => {
        return []; // No entities for this mock
    },
    getPollingInterval: () => {
        return 60000;
    },

    // Rendering
    getLayerConfig: () => {
        return {
            color: "#00FF00",
            clusterEnabled: false,
            clusterDistance: 50
        };
    },
    renderEntity: (entity) => {
        return {
            type: "point",
            color: "#00FF00",
            size: 5
        };
    },
    
    // Provide a UI component using the host's React instance
    getSidebarComponent: () => {
        // Access React from the global host object injected by WorldWideView
        const React = globalThis.__WWV_HOST__.React;
        
        if (!React) {
            console.error("[e2e-mock-plugin] Failed to resolve React from __WWV_HOST__");
            return null;
        }

        // Return a component function, not just an element
        return function MockSidebar() {
            return React.createElement(
                "div",
                { "data-testid": "e2e-mock-panel", style: { padding: "16px", background: "rgba(0, 255, 0, 0.1)", border: "1px solid green" } },
                "Mock Panel (E2E Test)"
            );
        };
    }
};
