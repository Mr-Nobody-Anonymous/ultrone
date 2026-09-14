/* ============================================================
   ULTRONE — Swarm Command & Control
   Boot, scroll engine, and live C2 simulation
   ============================================================ */
(() => {
  "use strict";

  /* ----------------------------------------------------------
     Global state
  ---------------------------------------------------------- */
  const state = {
    armed: false,          // master arm
    holdFire: false,
    stealth: false,
    sentry: false,
    autonomy: 75,          // 0-100 (maps to L1-L5)
    threat: 3,             // COND-1 .. COND-5
    simSpeed: 1,           // 0.25 .. 4
    domain: "air",
    locks: 0,
  };

  /* ----------------------------------------------------------
     Domain configuration
  ---------------------------------------------------------- */
  const domains = {
    air: {
      name: "Air Domain", icon: "✈️", color: "#00e5ff",
      threats: "8 Tracked", velocity: "Mach 2.4", posture: "Intercept Ready",
      nodes: "128 Active UAVs", nodeCount: 12,
      desc: "Multi-UAV supersonic swarm coordinated by Bayesian belief estimators and HTN backchaining.",
    },
    land: {
      name: "Land Domain", icon: "🛡️", color: "#34ffb0",
      threats: "14 Tracked", velocity: "65 km/h", posture: "Perimeter Locked",
      nodes: "64 Armed UGVs", nodeCount: 16,
      desc: "Autonomous ground combat vehicles executing MAPF swarm pathfinding across broken terrain.",
    },
    sea: {
      name: "Sea Domain", icon: "🚢", color: "#0090ff",
      threats: "3 Subsurface", velocity: "34 Knots", posture: "Acoustic Sweep",
      nodes: "32 USVs / UUVs", nodeCount: 9,
      desc: "Autonomous unmanned surface and underwater fleet safeguarding maritime transit corridors.",
    },
    space: {
      name: "Space Domain", icon: "🛰️", color: "#7c5cff",
      threats: "2 Orbital ASAT", velocity: "7.8 km/s", posture: "Constellation Mesh",
      nodes: "48 LEO Satellites", nodeCount: 14,
      desc: "LEO satellite constellation managing inter-satellite laser mesh networking and kinetic avoidance.",
    },
    cyber: {
      name: "Cyber Domain", icon: "⚡", color: "#ff2e88",
      threats: "1,420 pkts/s", velocity: "Sub-millisecond", posture: "Zero-Trust Active",
      nodes: "256 Mesh Nodes", nodeCount: 22,
      desc: "Autonomous cognitive defense engine countering zero-day exploits and DDoS attacks in real time.",
    },
  };

  const $ = (id) => document.getElementById(id);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));

  /* ----------------------------------------------------------
     Terminal logging (shared)
  ---------------------------------------------------------- */
  const termBody = $("terminalBody");
  function log(tag, msg, cls = "cyan") {
    if (!termBody) return;
    const row = document.createElement("div");
    row.className = "log-entry";
    const now = new Date().toTimeString().split(" ")[0];
    row.innerHTML =
      `<span class="log-time">[${now}]</span> ` +
      `<span class="log-tag ${cls}">[${tag}]</span> <span>${msg}</span>`;
    termBody.appendChild(row);
    termBody.scrollTop = termBody.scrollHeight;
  }

  /* ----------------------------------------------------------
     Boot sequence
  ---------------------------------------------------------- */
  const bootLines = [
    "initializing cognitive mesh…",
    "verifying 14 monorepo buckets… OK",
    "loading authoritative world model… 148 entities",
    "sensor fusion: satellite / sigint / radar / acoustic… SYNCED",
    "llm gateway multi-provider router… ONLINE",
    "swarm mesh handshake… 1,024 nodes linked",
    "all systems operational. welcome, operator.",
  ];

  function runBoot() {
    const screen = $("bootScreen");
    if (!screen) return;
    const lineEl = $("bootLine");
    const barEl = $("bootBar");
    document.body.style.overflow = "hidden";

    let li = 0;
    const lineInt = setInterval(() => {
      li++;
      if (li < bootLines.length && lineEl) {
        lineEl.textContent = bootLines[li];
      } else if (li >= bootLines.length) {
        clearInterval(lineInt);
      }
    }, 170);

    let p = 0;
    const barInt = setInterval(() => {
      p += Math.random() * 9 + 4;
      if (p >= 100) {
        p = 100;
        clearInterval(barInt);
        setTimeout(() => {
          screen.classList.add("done");
          document.body.style.overflow = "";
          requestAnimationFrame(() => revealInView());
        }, 350);
      }
      if (barEl) barEl.style.width = p + "%";
    }, 60);
  }

  /* ----------------------------------------------------------
     Scroll engine: reveals, progress, parallax, navbar
  ---------------------------------------------------------- */
  const revealEls = $$(".reveal");
  const parallaxEls = $$("[data-parallax]");

  function revealInView() {
    const vh = window.innerHeight;
    revealEls.forEach((el) => {
      if (el.classList.contains("in")) return;
      const r = el.getBoundingClientRect();
      if (r.top < vh * 0.88 && r.bottom > 0) {
        el.classList.add("in");
      }
    });
  }

  function onScroll() {
    // scroll progress
    const max = document.documentElement.scrollHeight - window.innerHeight;
    const pct = max > 0 ? (window.scrollY / max) * 100 : 0;
    const bar = $("scrollProgress");
    if (bar) bar.style.width = pct + "%";

    // navbar state
    const nav = $("navbar");
    if (nav) nav.classList.toggle("scrolled", window.scrollY > 40);

    // reveals
    revealInView();

    // parallax glows
    const y = window.scrollY;
    parallaxEls.forEach((el) => {
      const f = parseFloat(el.dataset.parallax) || 0;
      el.style.transform = `translateY(${y * f}px)`;
    });

    updateHorizontalScroll();
  }

  /* ----------------------------------------------------------
     Horizontal scroll domain deck
  ---------------------------------------------------------- */
  function updateHorizontalScroll() {
    const section = document.querySelector("#domains");
    const track = $("hscrollTrack");
    if (!section || !track) return;

    const rect = section.getBoundingClientRect();
    const total = section.offsetHeight - window.innerHeight;
    let p = -rect.top / total; // 0..1
    p = Math.max(0, Math.min(1, p));

    const maxScroll = track.scrollWidth - window.innerWidth;
    track.style.transform = `translate3d(${-p * maxScroll}px, 0, 0)`;

    // progress indicator
    const idx = Math.min(5, Math.max(1, Math.round(p * 4) + 1));
    const idxEl = $("hscrollIndex");
    if (idxEl) idxEl.textContent = String(idx).padStart(2, "0");
  }

  /* ----------------------------------------------------------
     Animated counters
  ---------------------------------------------------------- */
  function animateCounters() {
    $$(".counter").forEach((el) => {
      if (el.dataset.done) return;
      const target = parseFloat(el.dataset.target);
      const decimals = parseInt(el.dataset.decimals || "0", 10);
      const dur = 1400;
      const start = performance.now();
      el.dataset.done = "1";
      function tick(now) {
        const t = Math.min(1, (now - start) / dur);
        const eased = 1 - Math.pow(1 - t, 3);
        el.textContent = (target * eased).toFixed(decimals);
        if (t < 1) requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    });
  }

  /* ----------------------------------------------------------
     Clock + uptime
  ---------------------------------------------------------- */
  const bootTime = Date.now();
  function tickClock() {
    const clock = $("navClock");
    if (clock) clock.textContent = new Date().toTimeString().split(" ")[0];
    const up = $("uptimeEl");
    if (up) {
      const s = Math.floor((Date.now() - bootTime) / 1000);
      const h = String(Math.floor(s / 3600)).padStart(2, "0");
      const m = String(Math.floor((s % 3600) / 60)).padStart(2, "0");
      const sec = String(s % 60).padStart(2, "0");
      up.textContent = `${h}:${m}:${sec}`;
    }
  }

  /* ----------------------------------------------------------
     Radar viewport
  ---------------------------------------------------------- */
  const canvas = $("radarCanvas");
  const ctx = canvas ? canvas.getContext("2d") : null;
  let angle = 0;
  let targets = [];
  let scanSpeed = 0.035;

  function initTargets(count, color) {
    targets = [];
    if (!canvas) return;
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    const maxR = Math.min(cx, cy) * 0.85;
    for (let i = 0; i < count; i++) {
      const r = 40 + Math.random() * (maxR - 40);
      const theta = Math.random() * Math.PI * 2;
      targets.push({
        x: cx + r * Math.cos(theta), y: cy + r * Math.sin(theta),
        r, theta,
        speed: (Math.random() * 0.008 + 0.002) * (Math.random() > 0.5 ? 1 : -1),
        radiusDelta: (Math.random() - 0.5) * 0.4,
        size: Math.random() * 3 + 3, alpha: 0.2,
        color, locked: false,
        label: `TGT-${Math.floor(100 + Math.random() * 900)}`,
      });
    }
  }

  function resizeCanvas() {
    if (!canvas) return;
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;
    initTargets(domains[state.domain].nodeCount, domains[state.domain].color);
  }

  function drawRadar() {
    if (!canvas || !ctx) return;
    const w = canvas.width, h = canvas.height;
    const cx = w / 2, cy = h / 2;
    const maxR = Math.min(cx, cy) * 0.88;

    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = "rgba(2, 4, 10, 0.2)";
    ctx.fillRect(0, 0, w, h);

    // grid
    ctx.lineWidth = 1;
    ctx.strokeStyle = "rgba(0, 229, 255, 0.12)";
    for (let i = 1; i <= 4; i++) {
      ctx.beginPath();
      ctx.arc(cx, cy, (maxR / 4) * i, 0, Math.PI * 2);
      ctx.stroke();
    }
    ctx.beginPath();
    ctx.moveTo(cx - maxR, cy); ctx.lineTo(cx + maxR, cy);
    ctx.moveTo(cx, cy - maxR); ctx.lineTo(cx, cy + maxR);
    ctx.stroke();

    // sweep
    angle += scanSpeed * state.simSpeed;
    if (angle > Math.PI * 2) angle -= Math.PI * 2;
    const sweepX = cx + maxR * Math.cos(angle);
    const sweepY = cy + maxR * Math.sin(angle);

    ctx.save();
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, maxR, angle - 0.4, angle);
    ctx.closePath();
    ctx.fillStyle = "rgba(0, 229, 255, 0.08)";
    ctx.fill();
    ctx.restore();

    ctx.strokeStyle = state.stealth ? "rgba(0,229,255,0.25)" : domains[state.domain].color;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(sweepX, sweepY);
    ctx.stroke();

    // targets
    const hold = state.holdFire;
    targets.forEach((tgt) => {
      tgt.theta += tgt.speed * state.simSpeed;
      tgt.r += tgt.radiusDelta * state.simSpeed;
      if (tgt.r < 30 || tgt.r > maxR) tgt.radiusDelta *= -1;
      tgt.x = cx + tgt.r * Math.cos(tgt.theta);
      tgt.y = cy + tgt.r * Math.sin(tgt.theta);

      let diff = Math.abs(angle - tgt.theta);
      if (diff > Math.PI) diff = Math.PI * 2 - diff;
      if (diff < 0.2) tgt.alpha = 1.0;
      else tgt.alpha = Math.max(0.15, tgt.alpha - 0.015);

      const col = tgt.locked ? "#ff3b5c" : tgt.color;
      ctx.fillStyle = col;
      ctx.globalAlpha = tgt.alpha;
      ctx.beginPath();
      ctx.arc(tgt.x, tgt.y, tgt.size, 0, Math.PI * 2);
      ctx.fill();

      if (tgt.locked) {
        ctx.strokeStyle = "#ff3b5c";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(tgt.x, tgt.y, tgt.size + 5, 0, Math.PI * 2);
        ctx.stroke();
      }

      ctx.strokeStyle = col;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(tgt.x, tgt.y);
      ctx.lineTo(tgt.x + Math.cos(tgt.theta + Math.PI / 2) * 12, tgt.y + Math.sin(tgt.theta + Math.PI / 2) * 12);
      ctx.stroke();

      if (tgt.locked || tgt.alpha > 0.6) {
        ctx.font = "9px 'JetBrains Mono', monospace";
        ctx.fillStyle = "#fff";
        ctx.fillText(tgt.label, tgt.x + 8, tgt.y - 4);
      }
      ctx.globalAlpha = 1.0;
    });

    // sentry auto-lock
    if (state.sentry && !hold) {
      if (Math.random() < 0.02) {
        const unlocked = targets.filter((t) => !t.locked);
        if (unlocked.length) {
          unlocked[Math.floor(Math.random() * unlocked.length)].locked = true;
          updateLockCount();
        }
      }
    }

    requestAnimationFrame(drawRadar);
  }

  function updateLockCount() {
    const n = targets.filter((t) => t.locked).length;
    state.locks = n;
    if ($("hudLocks")) $("hudLocks").textContent = n;
    if ($("hudLockTotal")) $("hudLockTotal").textContent = targets.length;
  }

  function updateHUDStatus() {
    const el = $("hudStatus");
    if (!el) return;
    if (!state.armed) { el.textContent = "SAFE"; el.className = "hud-ok"; }
    else if (state.holdFire) { el.textContent = "HOLD FIRE"; el.className = "hud-warn"; }
    else { el.textContent = "WEAPONS FREE"; el.className = "hud-danger"; }
  }

  /* ----------------------------------------------------------
     Domain UI
  ---------------------------------------------------------- */
  function updateDomainUI(d) {
    if ($("domTitle")) $("domTitle").innerHTML = `${d.icon} ${d.name}`;
    if ($("domDesc")) $("domDesc").textContent = d.desc;
    if ($("domThreats")) $("domThreats").textContent = d.threats;
    if ($("domVelocity")) $("domVelocity").textContent = d.velocity;
    if ($("domPosture")) $("domPosture").textContent = d.posture;
    if ($("domNodes")) $("domNodes").textContent = d.nodes;
    if ($("hudDomain")) $("hudDomain").textContent = d.name.toUpperCase();
    if ($("hudNodes")) $("hudNodes").textContent = d.nodes.toUpperCase();
  }

  /* ----------------------------------------------------------
     Autonomy level mapping
  ---------------------------------------------------------- */
  function autonomyLevel(v) {
    if (v < 20) return { lvl: "L1", name: "Advise" };
    if (v < 40) return { lvl: "L2", name: "Suggest" };
    if (v < 60) return { lvl: "L3", name: "Approve" };
    if (v < 80) return { lvl: "L4", name: "Supervise" };
    return { lvl: "L5", name: "Autonomous" };
  }

  /* ----------------------------------------------------------
     Command feedback
  ---------------------------------------------------------- */
  function feedback(msg) {
    const el = $("commandFeedback");
    if (el) el.textContent = "> " + msg;
  }

  /* ----------------------------------------------------------
     Sync all control UI to state
  ---------------------------------------------------------- */
  function syncControls() {
    // master arm
    const arm = $("masterArm");
    if (arm) arm.classList.toggle("armed", state.armed);
    const armState = $("armState");
    if (armState) {
      armState.textContent = state.armed ? "ARMED" : "SAFE";
      armState.classList.toggle("armed", state.armed);
    }
    const armHint = $("armHint");
    if (armHint) armHint.textContent = state.armed
      ? "Engagement authority granted. Kinetic action authorized at autonomy ceiling."
      : "Engagement authority disabled. No kinetic action authorized.";

    // toggles
    syncToggle("holdFire", state.holdFire, true);
    syncToggle("stealth", state.stealth, false);
    syncToggle("sentry", state.sentry, false);

    // autonomy
    if ($("autonomySlider")) $("autonomySlider").value = state.autonomy;
    const a = autonomyLevel(state.autonomy);
    if ($("autonomyVal")) $("autonomyVal").textContent = `${a.lvl} // ${state.autonomy}%`;

    // sim speed
    if ($("simSpeedSlider")) $("simSpeedSlider").value = Math.round(state.simSpeed * 100);
    if ($("simSpeedVal")) $("simSpeedVal").textContent = "×" + state.simSpeed.toFixed(2);

    // threat posture
    $$("#threatSeg button").forEach((b) => {
      const on = parseInt(b.dataset.threat, 10) === state.threat;
      b.classList.toggle("active", on);
      b.classList.toggle("hot", state.threat >= 4);
    });
    if ($("threatVal")) $("threatVal").textContent = "COND-" + state.threat;
    const threatHint = $("threatHint");
    if (threatHint) {
      threatHint.textContent = state.threat >= 4
        ? "CRITICAL posture — full sensor saturation and priority targeting enabled."
        : state.threat <= 2
        ? "Relaxed posture — routine scan cadence and standard tracking."
        : "Heightened awareness — elevated scan rate & target tracking.";
    }

    // nav status pill
    const statusEl = $("navStatus");
    const statusText = $("navStatusText");
    if (statusEl && statusText) {
      statusEl.classList.remove("warn", "danger");
      if (!state.armed) { statusText.textContent = "SWARM ONLINE"; }
      else if (state.holdFire) { statusEl.classList.add("warn"); statusText.textContent = "HOLD FIRE"; }
      else { statusEl.classList.add("danger"); statusText.textContent = "WEAPONS FREE"; }
    }

    // command pod
    const pod = $("commandPod");
    if (pod) pod.classList.toggle("armed", state.armed);
    if ($("podMode")) $("podMode").textContent = state.armed ? "ARMED" : "SAFE";
    syncPodBtn("podHold", state.holdFire, true);
    syncPodBtn("podStealth", state.stealth, false);
    syncPodBtn("podSentry", state.sentry, false);

    updateHUDStatus();
  }

  function syncToggle(id, on, danger) {
    const el = $(id);
    if (!el) return;
    el.classList.toggle("on", on);
    el.classList.toggle("danger", on && danger);
    el.setAttribute("aria-checked", on ? "true" : "false");
  }

  function syncPodBtn(id, on, danger) {
    const el = $(id);
    if (!el) return;
    el.classList.toggle("active", on);
    el.classList.toggle("danger", on && danger);
  }

  /* ----------------------------------------------------------
     Sparkline
  ---------------------------------------------------------- */
  const spark = $("sparklineCanvas");
  const sparkCtx = spark ? spark.getContext("2d") : null;
  const sparkData = [];

  function drawSparkline() {
    if (!spark || !sparkCtx) return;
    const w = spark.width = spark.offsetWidth;
    const h = spark.height = spark.offsetHeight;
    sparkCtx.clearRect(0, 0, w, h);
    if (sparkData.length < 2) return;
    const max = Math.max(...sparkData) * 1.1;
    const grad = sparkCtx.createLinearGradient(0, 0, w, 0);
    grad.addColorStop(0, "#00e5ff");
    grad.addColorStop(1, "#7c5cff");
    sparkCtx.strokeStyle = grad;
    sparkCtx.lineWidth = 2;
    sparkCtx.beginPath();
    sparkData.forEach((v, i) => {
      const x = (i / (sparkData.length - 1)) * w;
      const y = h - (v / max) * h;
      i === 0 ? sparkCtx.moveTo(x, y) : sparkCtx.lineTo(x, y);
    });
    sparkCtx.stroke();
    // fill
    sparkCtx.lineTo(w, h);
    sparkCtx.lineTo(0, h);
    sparkCtx.closePath();
    const fill = sparkCtx.createLinearGradient(0, 0, 0, h);
    fill.addColorStop(0, "rgba(0,229,255,0.18)");
    fill.addColorStop(1, "rgba(0,229,255,0)");
    sparkCtx.fillStyle = fill;
    sparkCtx.fill();
  }

  /* ----------------------------------------------------------
     Vitals fluctuation
  ---------------------------------------------------------- */
  const vitals = [
    { fill: "meshLoad", pct: "meshPct", base: 42 },
    { fill: "worldLoad", pct: "worldPct", base: 61 },
    { fill: "fusionLoad", pct: "fusionPct", base: 87 },
    { fill: "gateLoad", pct: "gatePct", base: 24 },
  ];

  function updateVitals() {
    vitals.forEach((v) => {
      const val = Math.max(8, Math.min(98, v.base + (Math.random() * 18 - 9) + (state.sentry ? 6 : 0)));
      const fill = $(v.fill), pct = $(v.pct);
      if (fill) fill.style.width = val + "%";
      if (pct) pct.textContent = Math.round(val) + "%";
    });
    sparkData.push(40 + Math.random() * 55);
    if (sparkData.length > 60) sparkData.shift();
    drawSparkline();
  }

  /* ----------------------------------------------------------
     Wire up controls
  ---------------------------------------------------------- */
  function bindControls() {
    // Master arm
    const arm = $("masterArm");
    if (arm) arm.addEventListener("click", () => {
      state.armed = !state.armed;
      syncControls();
      feedback(state.armed ? "MASTER ARM ENGAGED — kinetic authority granted." : "MASTER ARM SAFE — kinetic authority revoked.");
      log("CMD", state.armed ? "Master arm ENGAGED. Weapons authority online." : "Master arm SAFE. Weapons authority revoked.", state.armed ? "red" : "green");
    });

    // Autonomy slider
    const aSlider = $("autonomySlider");
    if (aSlider) aSlider.addEventListener("input", () => {
      state.autonomy = parseInt(aSlider.value, 10);
      const a = autonomyLevel(state.autonomy);
      if ($("autonomyVal")) $("autonomyVal").textContent = `${a.lvl} // ${state.autonomy}%`;
      feedback(`Autonomy ceiling set to ${a.lvl} (${a.name}).`);
    });

    // Sim speed slider
    const sSlider = $("simSpeedSlider");
    if (sSlider) sSlider.addEventListener("input", () => {
      state.simSpeed = parseInt(sSlider.value, 10) / 100;
      if ($("simSpeedVal")) $("simSpeedVal").textContent = "×" + state.simSpeed.toFixed(2);
      feedback(`Simulation clock ${state.simSpeed.toFixed(2)}×.`);
    });

    // Threat posture
    $$("#threatSeg button").forEach((b) => {
      b.addEventListener("click", () => {
        state.threat = parseInt(b.dataset.threat, 10);
        syncControls();
        feedback(`Threat posture raised to COND-${state.threat}.`);
        log("POSTURE", `Threat condition COND-${state.threat}.`, state.threat >= 4 ? "red" : "amber");
      });
    });

    // Toggles
    const bindToggle = (id, key, danger, label) => {
      const el = $(id);
      if (!el) return;
      el.addEventListener("click", () => {
        state[key] = !state[key];
        syncControls();
        feedback(`${label} ${state[key] ? "ENGAGED" : "DISENGAGED"}.`);
        log(label.toUpperCase(), state[key] ? `${label} engaged.` : `${label} disengaged.`, state[key] && danger ? "red" : "green");
      });
    };
    bindToggle("holdFire", "holdFire", true, "Hold fire");
    bindToggle("stealth", "stealth", false, "Stealth mode");
    bindToggle("sentry", "sentry", false, "Sentry overwatch");

    // Pod buttons (mirror)
    if ($("podArm")) $("podArm").addEventListener("click", () => {
      state.armed = !state.armed; syncControls();
      log("CMD", state.armed ? "Master arm ENGAGED." : "Master arm SAFE.", state.armed ? "red" : "green");
    });
    if ($("podHold")) $("podHold").addEventListener("click", () => {
      state.holdFire = !state.holdFire; syncControls();
      log("CMD", state.holdFire ? "Hold fire engaged." : "Hold fire released.", state.holdFire ? "red" : "green");
    });
    if ($("podStealth")) $("podStealth").addEventListener("click", () => {
      state.stealth = !state.stealth; syncControls();
    });
    if ($("podSentry")) $("podSentry").addEventListener("click", () => {
      state.sentry = !state.sentry; syncControls();
    });

    // Domain buttons
    $$(".domain-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        $$(".domain-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        const dKey = btn.dataset.domain;
        if (domains[dKey]) {
          state.domain = dKey;
          updateDomainUI(domains[dKey]);
          initTargets(domains[dKey].nodeCount, domains[dKey].color);
          log("DOMAIN", `Operational theater switched to ${domains[dKey].name}.`);
        }
      });
    });

    // Radar click-to-lock
    if (canvas) {
      canvas.addEventListener("click", (e) => {
        const rect = canvas.getBoundingClientRect();
        const mx = (e.clientX - rect.left) * (canvas.width / rect.width);
        const my = (e.clientY - rect.top) * (canvas.height / rect.height);
        let best = null, bestD = 30;
        targets.forEach((t) => {
          const d = Math.hypot(t.x - mx, t.y - my);
          if (d < bestD) { bestD = d; best = t; }
        });
        if (best) {
          best.locked = !best.locked;
          updateLockCount();
          log("LOCK", `${best.label} ${best.locked ? "LOCKED" : "released"}.`, best.locked ? "red" : "cyan");
        }
      });
    }

    // Scramble + adapt
    if ($("btnScramble")) $("btnScramble").addEventListener("click", () => {
      if (!state.armed) {
        log("DENY", "Master arm is SAFE. Arm the system to authorize intercept.", "amber");
        feedback("Denied — master arm is SAFE.");
        return;
      }
      if (state.holdFire) {
        log("DENY", "Hold fire is engaged. Release hold fire to intercept.", "amber");
        return;
      }
      targets.forEach((t) => { t.locked = true; });
      updateLockCount();
      log("ENGAGE", `Autonomous intercept trajectories locked across ${domains[state.domain].name}.`, "red");
      feedback(`Intercept locked — ${targets.length} contacts designated.`);
    });

    if ($("btnAdapt")) $("btnAdapt").addEventListener("click", () => {
      log("EVO", "Evolutionary engine generated a new synergistic Course of Action (novelty 0.91).", "green");
    });

    // Terminal
    const termInput = $("terminalInput");
    if (termInput) termInput.addEventListener("keydown", (e) => {
      if (e.key !== "Enter") return;
      const val = termInput.value.trim().toLowerCase();
      termInput.value = "";
      if (!val) return;
      log("USER", val, "green");
      handleCommand(val);
    });
  }

  function handleCommand(cmd) {
    const [head, ...rest] = cmd.split(/\s+/);
    const arg = rest.join(" ");
    switch (head) {
      case "help":
        log("SYS", "commands: status · domains · scramble · mutate · arm · hold · stealth · sentry · autonomy <l1-l5> · threat <1-5> · speed <0.25-4> · benchmarks · clear", "amber");
        break;
      case "status":
        log("SYS", `Mesh 100% | Domain ${domains[state.domain].name} | Arm ${state.armed ? "ARMED" : "SAFE"} | Locks ${state.locks} | 2,248 tests passing`, "cyan");
        break;
      case "domains":
        log("SYS", "available: air, land, sea, space, cyber", "purple");
        break;
      case "scramble":
        if (!state.armed) { log("DENY", "Master arm is SAFE. Type 'arm' first.", "amber"); break; }
        if (state.holdFire) { log("DENY", "Hold fire is engaged.", "amber"); break; }
        targets.forEach((t) => { t.locked = true; });
        updateLockCount();
        log("ENGAGE", "Intercept trajectories locked on all radar contacts.", "red");
        break;
      case "mutate":
        log("EVOLVE", "Tactical genome mutated: action_weights.jam *= 1.15 · novelty 0.89.", "green");
        break;
      case "arm":
        state.armed = true; syncControls();
        log("CMD", "Master arm ENGAGED.", "red");
        break;
      case "disarm": case "safe":
        state.armed = false; syncControls();
        log("CMD", "Master arm SAFE.", "green");
        break;
      case "hold":
        state.holdFire = true; syncControls();
        log("CMD", "Hold fire engaged.", "red");
        break;
      case "release":
        state.holdFire = false; syncControls();
        log("CMD", "Hold fire released.", "green");
        break;
      case "stealth":
        state.stealth = !state.stealth; syncControls();
        log("CMD", `Stealth mode ${state.stealth ? "engaged" : "disengaged"}.`, "cyan");
        break;
      case "sentry":
        state.sentry = !state.sentry; syncControls();
        log("CMD", `Sentry overwatch ${state.sentry ? "engaged" : "disengaged"}.`, "green");
        break;
      case "autonomy": {
        const map = { l1: 10, l2: 30, l3: 50, l4: 75, l5: 95 };
        const key = arg.replace(/[^a-z0-9]/g, "");
        if (map[key]) { state.autonomy = map[key]; syncControls(); log("AUTO", `Autonomy ceiling ${autonomyLevel(state.autonomy).lvl}.`, "cyan"); }
        else log("ERR", "usage: autonomy l1..l5", "amber");
        break;
      }
      case "threat": {
        const n = parseInt(arg, 10);
        if (n >= 1 && n <= 5) { state.threat = n; syncControls(); log("POSTURE", `Threat condition COND-${n}.`, n >= 4 ? "red" : "amber"); }
        else log("ERR", "usage: threat 1..5", "amber");
        break;
      }
      case "speed": {
        const s = parseFloat(arg);
        if (s >= 0.25 && s <= 4) { state.simSpeed = s; syncControls(); log("CLOCK", `Simulation ${s}×.`, "cyan"); }
        else log("ERR", "usage: speed 0.25..4", "amber");
        break;
      }
      case "benchmarks":
        log("BENCH", "GSM8K 91.2% | MMLU 88.4% | HumanEval 94.6% | Combat latency 4.2ms", "purple");
        break;
      case "clear":
        termBody.innerHTML = "";
        break;
      default:
        log("ERR", `unknown command '${cmd}'. type 'help'.`, "amber");
    }
  }

  /* ----------------------------------------------------------
     Periodic telemetry stream
  ---------------------------------------------------------- */
  const events = [
    { tag: "FUSION", msg: "Satellite + SIGINT correlation confirmed at 97.4% confidence.", cls: "cyan" },
    { tag: "WORLD", msg: "Entity state updated in authoritative World Model: Air Asset-04.", cls: "green" },
    { tag: "HARNESS", msg: "Agent lifecycle healthy: heartbeat acknowledged (14ms).", cls: "purple" },
    { tag: "ROUTER", msg: "Multi-provider gateway routed query to fastest inference node.", cls: "cyan" },
    { tag: "MEMORY", msg: "Trajectory snapshot committed to collective memory vault.", cls: "purple" },
    { tag: "GAIT", msg: "Safety gate passed: COA novelty 0.91 within doctrine bounds.", cls: "green" },
  ];

  function startStreams() {
    setInterval(() => {
      const ev = events[Math.floor(Math.random() * events.length)];
      log(ev.tag, ev.msg, ev.cls);
    }, 6500);
    setInterval(updateVitals, 2200);
    setInterval(tickClock, 1000);
  }

  /* ----------------------------------------------------------
     Init
  ---------------------------------------------------------- */
  function init() {
    // seed terminal
    log("BOOT", "ULTRONE Cognitive Mesh Subsystem initialized. 14 monorepo buckets verified.", "cyan");
    log("WORLD", "Lattice WorldModel snapshot loaded: 148 tracked entities active.", "green");
    log("GATEWAY", "LLM Router operational across multi-provider endpoints.", "purple");

    bindControls();
    resizeCanvas();
    drawRadar();
    syncControls();
    updateLockCount();
    tickClock();

    // scroll listeners
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", () => { resizeCanvas(); onScroll(); });
    onScroll();

    // counters once visible
    const stats = document.querySelector(".stats-ribbon");
    if (stats && "IntersectionObserver" in window) {
      new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting) { animateCounters(); }
      }, { threshold: 0.3 }).observe(stats);
    } else {
      animateCounters();
    }

    requestAnimationFrame(runBoot);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
