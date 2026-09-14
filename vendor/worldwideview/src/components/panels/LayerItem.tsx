"use client";

/**
 * @file LayerItem.tsx
 * @description Individual layer item component used within the LayerPanel.
 * Displays plugin metadata, status indicators, and toggle controls.
 * @module src/components/panels
 */

import { useEffect, useState } from "react";
import { ShieldAlert, Wrench } from "lucide-react";
import { PluginIcon } from "@/components/common/PluginIcon";
import { Tooltip } from "@/components/ui/Tooltip";
import { getFreshness } from "@/core/data/freshness";
import { SeederEmptyChecklist } from "@/components/common/SeederEmptyChecklist";
import { pluginManager } from "@/core/plugins/PluginManager";
import type { WorldPlugin } from "@/core/plugins/PluginTypes";
import type { SeederHealth } from "@/core/state/seederHealthSlice";
import "./LayerItem.css";

// ─── Category Labels ────────────────────────────────────────

const CATEGORY_LABELS: Record<string, string> = {
    aviation: "Aviation",
    maritime: "Maritime",
    "natural-disaster": "Natural Disaster",
    conflict: "Conflict",
    infrastructure: "Infrastructure",
    cyber: "Cyber",
    economic: "Economic",
    custom: "Custom",
};

// ─── Source / Trust Helpers ─────────────────────────────────

function isLocalPlugin(pluginId: string): boolean {
    const manifest = pluginManager.getManifest(pluginId);
    if (!manifest) return true;
    const entry = manifest.entry ?? "";
    return entry.startsWith("/plugins-local/") || entry.startsWith("http://localhost") || entry.startsWith("http://127.0.0.1");
}

function TrustIcon({ pluginId, pluginName }: { pluginId: string; pluginName: string }) {
    if (isLocalPlugin(pluginId)) {
        return (
          <Tooltip content={`Local plugin: ${pluginName}`}>
            <span className="layer-item__local-icon-wrapper">
              <Wrench
                size={11}
                className="layer-item__local-icon"
                aria-label="Local plugin"
              />
            </span>
          </Tooltip>
        );
    }

    const manifest = pluginManager.getManifest(pluginId);
    if (manifest?.trust === "unverified") {
        return (
          <Tooltip content="Unverified plugin, use at your own risk">
            <span className="layer-item__unverified-icon-wrapper">
              <ShieldAlert
                size={12}
                className="layer-item__unverified-icon"
                aria-label="Unverified plugin"
              />
            </span>
          </Tooltip>
        );
    }

    return null;
}

// ─── Freshness Clock ───────────────────────────────────────

/** Re-renders the freshness tier every 30s so staleness colors advance without new data. */
function useNowMs(active: boolean): number {
    const [nowMs, setNowMs] = useState(() => Date.now());
    useEffect(() => {
        if (!active) return;
        const timer = setInterval(() => setNowMs(Date.now()), 30_000);
        return () => clearInterval(timer);
    }, [active]);
    return nowMs;
}

// ─── LayerItem Component ────────────────────────────────────

/**
 * @interface LayerItemProps
 * @description Properties for the LayerItem component.
 * @property {WorldPlugin} plugin - The plugin instance to represent.
 * @property {boolean} isEnabled - Whether the layer is currently active on the globe.
 * @property {boolean} isLoading - Whether the layer is currently fetching data.
 * @property {number} entityCount - The number of entities currently rendered for this layer.
 * @property {string} [fetchedAt] - Server-provided ISO timestamp of the latest snapshot, if any.
 * @property {boolean} [isSelected] - Whether this layer is focused in the config panel.
 * @property {function} onToggle - Callback to toggle the layer's enabled state.
 * @property {function} [onSelect] - Callback to focus the layer in the config panel.
 */
interface LayerItemProps {
    plugin: WorldPlugin;
    isEnabled: boolean;
    isLoading: boolean;
    entityCount: number;
    fetchedAt?: string;
    isSelected?: boolean;
    /** Total entities received for this layer (pre-budget). */
    totalEntityCount?: number;
    /** Entities actually rendering after budget thinning. */
    renderedCount?: number;
    /** True when the layer's feed exceeded its entity budget. */
    budgetExceeded?: boolean;
    onToggle: () => void;
    onSelect?: () => void;
    /** Optional seeder health used by the 'why is my layer empty?' checklist. */
    seederHealth?: SeederHealth;
}

/**
 * @component LayerItem
 * @description A list item representing a single data layer with status feedback.
 */
export function LayerItem({
    plugin,
    isEnabled,
    isLoading,
    entityCount,
    fetchedAt,
    isSelected,
    totalEntityCount,
    renderedCount,
    budgetExceeded,
    onToggle,
    onSelect,
    seederHealth,
}: LayerItemProps) {
    // Freshness renders only when the server provided fetchedAt — graceful degradation otherwise.
    const showFreshness = Boolean(fetchedAt) && isEnabled && !isLoading;
    const nowMs = useNowMs(showFreshness);
    const freshness = showFreshness ? getFreshness(fetchedAt, nowMs) : null;
    return (
      <div
        className={`layer-item ${isSelected ? "layer-item--selected" : ""}`}
        onClick={onSelect}
      >
        <span className="layer-item__icon">
          <PluginIcon icon={plugin.icon} size={18} />
        </span>

        <div className="layer-item__info">
          <div className="layer-item__header">
            <span className="layer-item__name">{plugin.name}</span>
            <TrustIcon pluginId={plugin.id} pluginName={plugin.name} />
          </div>
          <div className="layer-item__desc">{plugin.description}</div>
          <div className="layer-item__footer">
            {isEnabled && !isLoading && entityCount > 0 && (
              <span className="layer-item__count">
                {entityCount.toLocaleString()}
              </span>
                    )}
            {freshness && (
              <Tooltip content={freshness.title}>
                <span className={`layer-item__freshness layer-item__freshness--${freshness.tier}`}>
                  {freshness.label}
                </span>
              </Tooltip>
            )}
            {isEnabled && !isLoading && budgetExceeded && (
              <span
                className="layer-item__budget-badge"
                aria-label="Entity budget exceeded"
              >
                rendering {(renderedCount ?? entityCount).toLocaleString()} of {(totalEntityCount ?? entityCount).toLocaleString()}
              </span>
            )}
            {isEnabled && !isLoading && entityCount === 0 && (
              <div className="layer-item__empty-hint">
                <SeederEmptyChecklist health={seederHealth} />
              </div>
                    )}
          </div>
        </div>

        {isEnabled && isLoading && (
          <span className="layer-item__spinner" aria-label="Loading" />
            )}

        <div
          className={`layer-item__toggle ${isEnabled ? "layer-item__toggle--on" : ""}`}
          onClick={(e) => {
                    e.stopPropagation();
                    onToggle();
                }}
        />
      </div>
    );
}
