// ULTRONE Interactive Operational Platform
document.addEventListener("DOMContentLoaded", () => {
  // Domain Configurations
  const domains = {
    air: {
      name: "Air Domain",
      icon: "✈️",
      threats: "8 Tracked",
      velocity: "Mach 2.4",
      posture: "Intercept Ready",
      nodes: "128 Active UAVs",
      coa: "Combinatorial JAM + STRIKE Sync with RF mitigation",
      desc: "Multi-UAV supersonic swarm coordinated by Bayesian belief estimators and HTN backchaining.",
      color: "#00f3ff",
      nodeCount: 12
    },
    land: {
      name: "Land Domain",
      icon: "🛡️",
      threats: "14 Tracked",
      velocity: "65 km/h",
      posture: "Perimeter Locked",
      nodes: "64 Armed UGVs",
      coa: "Terrain-gradient ambush corridor with dynamic minefields",
      desc: "Autonomous ground combat vehicles executing MAPF swarm pathfinding across broken terrain.",
      color: "#00ff9d",
      nodeCount: 16
    },
    sea: {
      name: "Sea Domain",
      icon: "🚢",
      threats: "3 Subsurface",
      velocity: "34 Knots",
      posture: "Acoustic Sweep",
      nodes: "32 USVs / UUVs",
      coa: "Distributed acoustic sonar triangulation & choke blockade",
      desc: "Autonomous unmanned surface and underwater fleet safeguarding maritime transit corridors.",
      color: "#00a2ff",
      nodeCount: 8
    },
    space: {
      name: "Space Domain",
      icon: "🛰️",
      threats: "2 Orbital ASAT",
      velocity: "7.8 km/s",
      posture: "Constellation Mesh",
      nodes: "48 LEO Satellites",
      coa: "Proactive orbital evasion maneuver & laser crosslink sync",
      desc: "LEO satellite constellation managing inter-satellite laser mesh networking and kinetic avoidance.",
      color: "#a855f7",
      nodeCount: 14
    },
    cyber: {
      name: "Cyber Domain",
      icon: "⚡",
      threats: "1,420 pkts/s",
      velocity: "Sub-millisecond",
      posture: "Zero-Trust Active",
      nodes: "256 Mesh Nodes",
      coa: "Real-time polymorphic network micro-segmentation",
      desc: "Autonomous cognitive defense engine countering zero-day exploits and DDoS attacks in real time.",
      color: "#ff3366",
      nodeCount: 22
    }
  };

  let currentDomain = "air";

  // Radar Canvas Simulation
  const canvas = document.getElementById("radarCanvas");
  const ctx = canvas ? canvas.getContext("2d") : null;
  let angle = 0;
  let targets = [];

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
        x: cx + r * Math.cos(theta),
        y: cy + r * Math.sin(theta),
        r: r,
        theta: theta,
        speed: (Math.random() * 0.008 + 0.002) * (Math.random() > 0.5 ? 1 : -1),
        radiusDelta: (Math.random() - 0.5) * 0.4,
        size: Math.random() * 3 + 3,
        alpha: 0.2,
        color: color,
        locked: false,
        label: `TGT-${Math.floor(100 + Math.random() * 900)}`
      });
    }
  }

  function resizeCanvas() {
    if (!canvas) return;
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;
    initTargets(domains[currentDomain].nodeCount, domains[currentDomain].color);
  }

  window.addEventListener("resize", resizeCanvas);

  function drawRadar() {
    if (!canvas || !ctx) return;
    const w = canvas.width;
    const h = canvas.height;
    const cx = w / 2;
    const cy = h / 2;
    const maxR = Math.min(cx, cy) * 0.88;

    ctx.fillStyle = "rgba(2, 4, 10, 0.25)";
    ctx.fillRect(0, 0, w, h);

    // Grid circles
    ctx.lineWidth = 1;
    ctx.strokeStyle = "rgba(0, 243, 255, 0.12)";
    for (let i = 1; i <= 4; i++) {
      ctx.beginPath();
      ctx.arc(cx, cy, (maxR / 4) * i, 0, Math.PI * 2);
      ctx.stroke();
    }

    // Crosshairs
    ctx.beginPath();
    ctx.moveTo(cx - maxR, cy);
    ctx.lineTo(cx + maxR, cy);
    ctx.moveTo(cx, cy - maxR);
    ctx.lineTo(cx, cy + maxR);
    ctx.stroke();

    // Radar Sweep Line
    angle += 0.035;
    if (angle > Math.PI * 2) angle -= Math.PI * 2;

    const sweepX = cx + maxR * Math.cos(angle);
    const sweepY = cy + maxR * Math.sin(angle);

    // Gradient Sweep Cone
    const sweepGrad = ctx.createRadialGradient(cx, cy, 10, cx, cy, maxR);
    sweepGrad.addColorStop(0, "rgba(0, 243, 255, 0.2)");
    sweepGrad.addColorStop(1, "transparent");

    ctx.save();
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, maxR, angle - 0.4, angle);
    ctx.closePath();
    ctx.fillStyle = "rgba(0, 243, 255, 0.08)";
    ctx.fill();
    ctx.restore();

    // Sweep Line
    ctx.strokeStyle = domains[currentDomain].color;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(sweepX, sweepY);
    ctx.stroke();

    // Targets
    targets.forEach((tgt) => {
      tgt.theta += tgt.speed;
      tgt.r += tgt.radiusDelta;
      if (tgt.r < 30 || tgt.r > maxR) tgt.radiusDelta *= -1;

      tgt.x = cx + tgt.r * Math.cos(tgt.theta);
      tgt.y = cy + tgt.r * Math.sin(tgt.theta);

      // Check if sweep is near target
      let diff = Math.abs(angle - tgt.theta);
      if (diff > Math.PI) diff = Math.PI * 2 - diff;
      if (diff < 0.2) {
        tgt.alpha = 1.0;
      } else {
        tgt.alpha = Math.max(0.2, tgt.alpha - 0.015);
      }

      ctx.fillStyle = tgt.locked ? "#ff3366" : tgt.color;
      ctx.globalAlpha = tgt.alpha;
      ctx.beginPath();
      ctx.arc(tgt.x, tgt.y, tgt.size, 0, Math.PI * 2);
      ctx.fill();

      // Heading vector
      ctx.strokeStyle = tgt.color;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(tgt.x, tgt.y);
      ctx.lineTo(tgt.x + Math.cos(tgt.theta + Math.PI/2) * 12, tgt.y + Math.sin(tgt.theta + Math.PI/2) * 12);
      ctx.stroke();

      if (tgt.locked || tgt.alpha > 0.6) {
        ctx.font = "9px 'JetBrains Mono', monospace";
        ctx.fillStyle = "#fff";
        ctx.fillText(tgt.label, tgt.x + 8, tgt.y - 4);
      }
      ctx.globalAlpha = 1.0;
    });

    requestAnimationFrame(drawRadar);
  }

  // Domain Switcher Buttons
  const domainBtns = document.querySelectorAll(".domain-btn");
  domainBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      domainBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const dKey = btn.dataset.domain;
      if (domains[dKey]) {
        currentDomain = dKey;
        updateDomainUI(domains[dKey]);
        initTargets(domains[dKey].nodeCount, domains[dKey].color);
        addTerminalLog("DOMAIN", `Switched operational theater to ${domains[dKey].name}.`, "cyan");
      }
    });
  });

  function updateDomainUI(d) {
    document.getElementById("domTitle").innerHTML = `${d.icon} ${d.name}`;
    document.getElementById("domDesc").textContent = d.desc;
    document.getElementById("domThreats").textContent = d.threats;
    document.getElementById("domVelocity").textContent = d.velocity;
    document.getElementById("domPosture").textContent = d.posture;
    document.getElementById("domNodes").textContent = d.nodes;
    document.getElementById("hudDomain").textContent = d.name.toUpperCase();
    document.getElementById("hudNodes").textContent = d.nodes.toUpperCase();
  }

  // Interactive Terminal
  const termBody = document.getElementById("terminalBody");
  const termInput = document.getElementById("terminalInput");

  function addTerminalLog(tag, msg, tagClass = "cyan") {
    if (!termBody) return;
    const row = document.createElement("div");
    row.className = "log-entry";
    const now = new Date().toTimeString().split(" ")[0];
    row.innerHTML = `<span class="log-time">[${now}]</span> <span class="log-tag ${tagClass}">[${tag}]</span> <span>${msg}</span>`;
    termBody.appendChild(row);
    termBody.scrollTop = termBody.scrollHeight;
  }

  if (termInput) {
    termInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        const val = termInput.value.trim().toLowerCase();
        termInput.value = "";
        if (!val) return;

        addTerminalLog("USER", val, "green");

        if (val === "help") {
          addTerminalLog("SYS", "Commands: status, domains, scramble, mutate, benchmarks, clear", "amber");
        } else if (val === "status") {
          addTerminalLog("SYS", `Mesh Health: 100% | Active Domain: ${domains[currentDomain].name} | 2,248 tests passing`, "cyan");
        } else if (val === "domains") {
          addTerminalLog("SYS", "Available domains: air, land, sea, space, cyber", "purple");
        } else if (val === "scramble") {
          targets.forEach(t => t.locked = true);
          addTerminalLog("ENGAGE", "Autonomous intercept trajectories locked on all radar targets.", "amber");
        } else if (val === "mutate") {
          addTerminalLog("EVOLVE", "Tactical genome mutated: action_weights.jam *= 1.15. Novelty: 0.89.", "green");
        } else if (val === "benchmarks") {
          addTerminalLog("BENCH", "GSM8K: 91.2% | MMLU: 88.4% | HumanEval: 94.6% | Combat Latency: 4.2ms", "purple");
        } else if (val === "clear") {
          termBody.innerHTML = "";
        } else {
          addTerminalLog("ERR", `Unknown command: '${val}'. Type 'help' for options.`, "amber");
        }
      }
    });
  }

  // Action Buttons
  const btnScramble = document.getElementById("btnScramble");
  if (btnScramble) {
    btnScramble.addEventListener("click", () => {
      targets.forEach(t => t.locked = true);
      addTerminalLog("CMD", `Scrambled countermeasures across ${domains[currentDomain].name}!`, "amber");
    });
  }

  const btnAdapt = document.getElementById("btnAdapt");
  if (btnAdapt) {
    btnAdapt.addEventListener("click", () => {
      addTerminalLog("EVO", "Evolutionary combat engine generated new synergistic Course of Action (COA).", "green");
    });
  }

  // Periodic Telemetry Stream
  const simulatedEvents = [
    { tag: "FUSION", msg: "Satellite + SIGINT correlation confirmed at 97.4% confidence.", cls: "cyan" },
    { tag: "WORLD", msg: "Entity state updated in authoritative World Model: Air Asset-04.", cls: "green" },
    { tag: "HARNESS", msg: "Agent lifecycle healthy: Heartbeat acknowledged (14ms latency).", cls: "purple" },
    { tag: "ROUTER", msg: "Multi-provider model gateway routed query to fastest inference node.", cls: "cyan" }
  ];

  setInterval(() => {
    const ev = simulatedEvents[Math.floor(Math.random() * simulatedEvents.length)];
    addTerminalLog(ev.tag, ev.msg, ev.cls);
  }, 7000);

  // Initial setup
  resizeCanvas();
  drawRadar();
});
