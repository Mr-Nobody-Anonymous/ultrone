"use client";

/**
 * @file SeederEmptyChecklist.tsx
 * @description 'Why is my layer empty?' checklist panel. Rendered from a
 * collapsed section next to a plugin row (or reachable from an empty layer).
 *
 * It is a STATIC checklist: the rows are derived from the same
 * server-computed SeederHealth object used by the freshness badge. There are
 * no interactive diagnostics and no state machine — deeper triage is
 * explicitly out of scope.
 */

import { useState } from "react";
import { deriveSeederChecklist } from "@/lib/seederHealthBadge";
import type { SeederHealth } from "@/core/state/seederHealthSlice";
import "./SeederEmptyChecklist.css";

export function SeederEmptyChecklist({ health }: { health: SeederHealth | undefined }) {
    const [open, setOpen] = useState(false);
    const rows = deriveSeederChecklist(health);
    const hasHealth = health !== undefined && health !== null;

    return (
      <div className="seeder-empty-checklist">
        <button
          type="button"
          className="seeder-empty-checklist__toggle"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
        >
          {open ? "Hide" : "Why is my layer empty?"}
        </button>

        {open && (
          <ul className="seeder-empty-checklist__rows">
            {rows.map((row) => (
              <li
                key={row.id}
                className={`seeder-empty-checklist__row ${row.suspect ? "seeder-empty-checklist__row--suspect" : ""}`}
              >
                <span className="seeder-empty-checklist__box" aria-hidden="true">
                  {row.suspect ? "✕" : "✓"}
                </span>
                {row.label}
              </li>
            ))}
            {!hasHealth && (
              <li className="seeder-empty-checklist__row">
                <span className="seeder-empty-checklist__box" aria-hidden="true">?</span>
                Tip: enable the Data Layers toggle and wait for the seeder to run for the first time.
              </li>
            )}
          </ul>
        )}
      </div>
    );
}
