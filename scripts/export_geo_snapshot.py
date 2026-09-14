#!/usr/bin/env python3
"""Export a static ULTRONE geo snapshot for offline/static hosting.

The Global Eye globe (``apps/globe``) normally reads live entities from the
Python geo API (``/api/ultrone/entities``). Static hosts such as GitHub Pages
have no Python backend, so the deployment pipeline bakes one representative
snapshot (demo theater + simulated RED/BLUE tracks) into a JSON file that the
globe falls back to when the API is unreachable.

Usage:
    python scripts/export_geo_snapshot.py apps/globe/public/ultrone-demo-snapshot.json

Requires only the standard library plus numpy (for the sim env).
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path


def _stub_brain_perception() -> None:
    """Neutralize the sim env's optional AI-perception import.

    ``BattlefieldEnv._get_observation`` does
    ``from brain.perception.specialized_analyzers import RadarAI, VisualAI``
    and wraps every use in ``try/except`` with dict fallbacks. Pre-seeding
    ``sys.modules`` with raising stubs keeps the export hermetic (no torch /
    transformers / network) while the env records its normal fallbacks.
    """

    class _OfflineAnalyzer:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def analyze(self, *args, **kwargs):
            raise RuntimeError("offline snapshot: no AI perception")

    brain = types.ModuleType("brain")
    perception = types.ModuleType("brain.perception")
    analyzers = types.ModuleType("brain.perception.specialized_analyzers")
    analyzers.RadarAI = _OfflineAnalyzer
    analyzers.VisualAI = _OfflineAnalyzer
    sys.modules.setdefault("brain", brain)
    sys.modules.setdefault("brain.perception", perception)
    sys.modules["brain.perception.specialized_analyzers"] = analyzers


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <output.json>", file=sys.stderr)
        return 2
    out = Path(sys.argv[1])

    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root))
    from _ultrone_paths import ensure_on_syspath

    ensure_on_syspath(root)

    from world_model import WorldModel

    from packages.geospatial.service import GeoService

    # The sim env's observation path imports the brain perception stack
    # (torch/transformers + network weight downloads) purely to annotate
    # observations. A static snapshot only needs grid positions, so stub the
    # analyzers out: the env's own try/except then records its documented
    # fallback dicts. This keeps the export stdlib+numpy-only.
    _stub_brain_perception()

    svc = GeoService(world_model=WorldModel(), seed_demo=True)
    svc.attach_sim()
    svc.step_sim(3)
    snapshot = svc.snapshot()
    # Let the globe animate the static picture: advance the demo clock a few
    # ticks so bundled tracks already have visible trails.
    for _ in range(4):
        svc.tick()
        snapshot = svc.snapshot(advance=False)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, indent=1), encoding="utf-8")
    print(
        f"wrote {out} ({snapshot['count']} entities, "
        f"{len(snapshot['tracks'])} tracks)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
