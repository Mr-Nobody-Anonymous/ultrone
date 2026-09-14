"use client";

/**
 * @file SeederHealthBadge.tsx
 * @description Small freshness badge for a plugin's seeder, rendered in the
 * PluginsTab row. Derives entirely from the server-computed SeederHealth
 * record (never from client-side clock math). No health data -> renders
 * nothing (graceful).
 */

import { deriveSeederBadge } from "@/lib/seederHealthBadge";
import type { SeederHealth } from "@/core/state/seederHealthSlice";
import "./SeederHealthBadge.css";

export function SeederHealthBadge({ health }: { health: SeederHealth | undefined }) {
    const badge = deriveSeederBadge(health);
    if (!badge) return null;

    return (
      <span
        className={`seeder-health-badge seeder-health-badge--${badge.state}`}
        title={badge.title}
        data-testid="seeder-health-badge"
      >
        {badge.label}
      </span>
    );
}
