"""Validate the reorganized ULTRONE monorepo: bootstrap + imports + paths."""
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

out = []
def log(msg):
    out.append(str(msg))
    print(msg)

# 1. Bootstrap
from _ultrone_paths import ensure_on_syspath, BUCKETS
root = ensure_on_syspath(ROOT)
log(f"repo root: {root}")
missing = [b for b in BUCKETS if not (root / b).is_dir()]
log(f"buckets listed: {len(BUCKETS)}, missing dirs: {missing or 'none'}")

failures = []

# 2. Import checks across every bucket (original names)
IMPORTS = [
    # apps
    ("ultrone_hitl", None),
    ("ultrone_hitl.api", None),
    # packages/core
    ("core.contracts", None),
    ("config.settings", None),
    ("utils.helpers", None),
    ("datasets.registry", None),
    ("extension_log.stores", None),
    ("world_model", None),
    # packages/cognition
    ("brain.orchestrator", None),
    ("brain.perception.situational_awareness.world_model", None),
    ("cognitive.cognitive_loop", None),
    ("frontier.reasoning", None),
    ("sandbox.ucl", None),
    ("self_improvement.improvement_loop", None),
    ("evolution", None),
    ("game_ai", None),
    ("generative", None),
    ("ultrone_ai", None),
    # packages/agents
    ("agents", None),
    ("agents.commands", None),
    ("agents.civilian", None),
    ("ai_architectures", None),
    ("coding_agent", None),
    ("plugin_sdk", None),
    ("robotics", None),
    ("ultrone_bindings", None),
    # packages/knowledge
    ("knowledge_engine", None),
    ("learning", None),
    ("mlops", None),
    ("training_platform", None),
    ("memory_cluster", None),
    # packages/orchestration
    ("orchestration", None),
    # packages/runtime
    ("runtime", None),
    ("compiler", None),
    ("hardware", None),
    ("ultrone_os", None),
    ("ultrone_rt", None),
    ("ultrone_bindings", None),
    # packages/safety / observability / transport
    ("security", None),
    ("viz", None),
    ("comms", None),
    # research
    ("research_db", None),
    ("research_db.store", None),
    ("research_db.schema", None),
    ("research_division", None),
    ("benchmarks", None),
    ("benchmarks.canonical.research_sink", None),
    # simulation
    ("sim", None),
    ("simulation", None),
    # vendor
    ("ultron", None),
    ("ultron.api.paths", None),
    ("ultron.core.models", None),
]

for module_name, _ in IMPORTS:
    try:
        __import__(module_name)
        log(f"OK    import {module_name}")
    except Exception as exc:
        failures.append((module_name, repr(exc)))
        log(f"FAIL  import {module_name}: {exc!r}")

# 3. World model + adapters smoke
try:
    from world_model import Entity, WorldModel, EntityUpdated, Provenance
    wm = WorldModel()
    e = Entity(entity_id="entity_001", type="air_asset")
    e.set("position", {"lat": 10.0, "lon": 20.0}, confidence=0.87,
          provenance=[Provenance(source="sensor:radar-3", transformation="sensor_fusion")])
    wm.upsert(e)
    snap = wm.snapshot()
    assert snap and snap[0]["components"]["position"]["confidence"] == 0.87
    ev = EntityUpdated(entity_id="entity_001", changes={"status": "engaged"},
                       confidence=0.91)
    wm.apply(ev)
    assert wm.get("entity_001").get("status") == "engaged"
    log("OK    world_model smoke (entity -> event -> state)")
except Exception as exc:
    failures.append(("world_model smoke", repr(exc)))
    log(f"FAIL  world_model smoke: {exc!r}")

try:
    from adapters.base import BaseAdapter
    from adapters.llm import LLMAdapter
    from adapters.vision import VisionAdapter
    from adapters.vector_db import VectorDBAdapter
    from adapters.database import DatabaseAdapter
    from adapters.external import ExternalAdapter
    a = LLMAdapter()
    h = a.health()
    assert h["available"] is False
    log("OK    adapters ports import + placeholder health")
except Exception as exc:
    failures.append(("adapters", repr(exc)))
    log(f"FAIL  adapters: {exc!r}")

# 4. Vendored path constants resolve to real locations
try:
    from ultron.api.paths import DASHBOARD_DIR, AGENT_SKILL_PACKAGE_DIR, SKILLS_ROOT
    log(f"OK    vendored paths: DASHBOARD_DIR={DASHBOARD_DIR} exists={Path(DASHBOARD_DIR).is_dir()}")
    log(f"      SKILLS_ROOT={SKILLS_ROOT} exists={Path(SKILLS_ROOT).is_dir()}")
    log(f"      AGENT_SKILL_PACKAGE_DIR exists={Path(AGENT_SKILL_PACKAGE_DIR).is_dir()}")
    assert Path(AGENT_SKILL_PACKAGE_DIR).is_dir(), "skill package missing"
    assert Path(SKILLS_ROOT).is_dir(), "skills root missing"
except Exception as exc:
    failures.append(("vendored paths", repr(exc)))
    log(f"FAIL  vendored paths: {exc!r}")

# 5. research_db store writes into its package dir (no CWD dependence)
try:
    import tempfile
    from research_db.store import JSONResearchStore, ResearchDatabase
    with tempfile.TemporaryDirectory() as tmp:
        db = ResearchDatabase()  # default -> package dir
        expected = root / "research" / "research_db"
        assert db.store.base_dir == expected, (db.store.base_dir, expected)
        log("OK    ResearchDatabase() default dir == package dir")
        store = JSONResearchStore(base_dir=tmp)
        log("OK    JSONResearchStore(tmp) explicit base_dir")
except Exception as exc:
    failures.append(("research_db store", repr(exc)))
    log(f"FAIL  research_db store: {exc!r}")

log("")
log(f"IMPORTS OK: {sum(1 for m, _ in IMPORTS) - sum(1 for m, _ in failures if (m, _))}")
log(f"TOTAL FAILURES: {len(failures)}")
for name, exc in failures:
    log(f"  - {name}: {exc}")

with io.open(ROOT / "_validation.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
sys.exit(1 if failures else 0)
