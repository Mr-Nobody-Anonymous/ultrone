# Deploying ULTRONE Research — free, public, simulation-only

This repo deploys in two halves that never mix:

```
GitHub (this repository)
│
├── Actions  → full test suite on Python 3.10/3.11/3.12
│             (research-platform-ci.yml — already configured)
│
└── push ──► deploy-hf-space.yml
              │  stages ONLY: app + agents/ sandbox/ data/ comms/
              ▼
       Hugging Face Space  "ULTRONE Research"
              │  Gradio demo (CPU) — deterministic, no GPU required
              ▼
       synthetic aircraft / vehicles / vessels / spacecraft /
       robots / plants / network nodes
```

**Safety scoping:** the Space ships a curated slice — the sandbox fleet,
universal control layer, subsystem library, and the civilian / robotics /
infrastructure platform packages. The tactical domain modules are not
part of the deployed payload, the UI cannot reach them, and a unit test
(`tests/test_deploy_demo.py`) enforces the import allowlist. Everything
deployed is deterministic simulation with no path to real systems.

---

## One-time setup (~5 minutes)

1. **Create the token**: huggingface.co → Settings → Access Tokens →
   create a token with **write** scope.
2. **Add the GitHub secret**: repo → Settings → Secrets and variables →
   Actions → new secret `HF_TOKEN` = that token.
3. **Add the repository variable**: same page → Variables tab → new
   variable `SPACE_REPO_ID` = `yourname/ultrone-research`.
4. Push to `main` (or run the *Deploy ULTRONE Research Space* workflow
   manually). The first run creates the Space; subsequent pushes update
   it and the Space rebuilds automatically.

That's it — GitHub stays your source of truth and the Space is the live
demo.

---

## What the free tier actually gives you (verified against HF docs)

| Item | Free account reality |
|---|---|
| Hosting this demo | **CPU basic is free and unlimited** — this demo needs no GPU |
| Hosting ZeroGPU Spaces | Up to **2** for personal accounts in good standing (PRO: 10) |
| ZeroGPU *usage* quota | 2 min/day unauthenticated visitors, **5 min/day** free sign-ins, 40 min/day PRO |
| ZeroGPU hardware | NVIDIA RTX Pro 6000 Blackwell, dynamically allocated |
| Quota reset | 24 h after first GPU use of the day |

Because the architecture demo is deterministic CPU code, it costs $0
forever and never queues.

## If/when you attach a real model later

The demo intentionally has **no model behind reasoning yet** — compute
alone doesn't add intelligence, and ULTRONE's orchestration works
model-free today. When you do want an LLM in the loop:

1. Add a GPU-backed inference function to `app.py`:

   ```python
   import spaces            # provided automatically on ZeroGPU Spaces

   @spaces.GPU(duration=60)  # short duration = better queue priority
   def reason(prompt: str) -> str:
       ...                   # load a quantized open-weight model here
   ```

2. Bump the Space hardware to **ZeroGPU** in Settings.
3. Budget by the table above: a 5-min/day free visitor quota means the
   LLM is a demo garnish, not a workhorse. Optimize accordingly
   (quantization, small models, caching).

## Troubleshooting

- **Deploy fails with "Set SPACE_REPO_ID"** → you skipped step 3.
- **401/403 from HF** → token lacks write scope or expired.
- **Files >10 MB** would need Git-LFS on the Hub side; nothing in the
  staged payload comes close.
- **Space build errors** → check the Space's logs tab; the staged
  runtime is just `gradio` plus stdlib-pure Python, so failures are
  almost always version pins in `deploy/hf_space/requirements.txt`.
