"""Agent management and inspection API."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

AGENTS_DB: Dict[str, Dict[str, Any]] = {
    "agent-001": {
        "id": "agent-001",
        "type": "drone",
        "domain": "air",
        "status": "active",
        "position": [42.3601, -71.0589],
        "health": 0.92,
        "fuel": 0.68,
        "planner": "MCTS",
        "optimizer": "PPO",
        "policy": "epsilon-greedy",
        "confidence": 0.87,
        "beliefs": ["enemy detected at bearing 045", "supply line secure", "weather deteriorating"],
        "goals": ["patrol sector alpha", "maintain comm relay", "identify threats"],
        "intentions": ["move to waypoint B4", "activate ECM"],
        "utility": {"offensive": 0.7, "defensive": 0.5, "recon": 0.8},
        "memory": {
            "episodic": [{"event": "engaged enemy drone", "outcome": "victory", "importance": 0.9}],
            "semantic": ["enemy uses swarm tactics", "ECM effective at range > 500m"],
        },
        "decision_history": [
            {"time": 12, "action": "move", "reasoning": "advance to contact", "alternatives": ["wait", "retreat"]},
            {"time": 24, "action": "engage", "reasoning": "hostile track confirmed", "alternatives": ["jam", "evade"]},
            {"time": 36, "action": "jam", "reasoning": "suppress enemy radar", "alternatives": ["strike", "reposition"]},
        ],
        "knowledge_graph": {
            "nodes": [{"id": "enemy_radar", "type": "threat"}, {"id": "supply_route_a", "type": "asset"}],
            "edges": [{"source": "enemy_radar", "target": "supply_route_a", "relation": "threatens"}],
        },
    },
    "agent-002": {
        "id": "agent-002",
        "type": "fighter",
        "domain": "air",
        "status": "engaged",
        "position": [42.3650, -71.0650],
        "health": 0.75,
        "fuel": 0.45,
        "planner": "HTN",
        "optimizer": "SAC",
        "policy": "gaussian",
        "confidence": 0.93,
        "beliefs": ["bandit at angels 15", "missile inbound", "wingman in formation"],
        "goals": ["achieve intercept geometry", "maintain energy advantage"],
        "intentions": ["break left", "deploy countermeasures", "engage afterburner"],
        "utility": {"offensive": 0.9, "defensive": 0.6, "recon": 0.3},
        "memory": {
            "episodic": [{"event": "BVR engagement", "outcome": "kill", "importance": 0.8}],
            "semantic": ["merge at 20nm", "Fox-3 at 15nm"],
        },
        "decision_history": [
            {"time": 8, "action": "climb", "reasoning": "gain energy advantage", "alternatives": ["turn", "dive"]},
            {"time": 16, "action": "lock", "reasoning": "STT established", "alternatives": ["TWS", "visual"]},
        ],
        "knowledge_graph": {
            "nodes": [{"id": "bandit_1", "type": "hostile"}, {"id": "wingman_2", "type": "friendly"}],
            "edges": [{"source": "bandit_1", "target": "wingman_2", "relation": "engaged"}],
        },
    },
    "agent-003": {
        "id": "agent-003",
        "type": "tank",
        "domain": "land",
        "status": "active",
        "position": [42.3500, -71.0700],
        "health": 1.0,
        "fuel": 0.82,
        "planner": "AStar",
        "optimizer": "DQN",
        "policy": "epsilon-greedy",
        "confidence": 0.79,
        "beliefs": ["infantry squad advancing", "bridge intact", "possible ambush at grid 7"],
        "goals": ["provide fire support", "secure crossroad"],
        "intentions": ["move to hull-down position", "observe sector"],
        "utility": {"offensive": 0.6, "defensive": 0.8, "recon": 0.4},
        "memory": {
            "episodic": [{"event": "urban engagement", "outcome": "objective secure", "importance": 0.7}],
            "semantic": ["main gun effective to 2500m", "side armor vulnerable"],
        },
        "decision_history": [
            {"time": 5, "action": "move", "reasoning": "advance to firing position", "alternatives": ["hold", "reposition"]},
            {"time": 15, "action": "engage", "reasoning": "enemy armor sighted", "alternatives": ["call_for_fire", "suppress"]},
        ],
        "knowledge_graph": {
            "nodes": [{"id": "infantry_platoon", "type": "friendly"}, {"id": "enemy_apc", "type": "hostile"}],
            "edges": [{"source": "enemy_apc", "target": "infantry_platoon", "relation": "threatens"}],
        },
    },
}


@router.get("/")
async def list_agents() -> List[Dict[str, Any]]:
    """List all agents."""
    return [{"id": a["id"], "type": a["type"], "domain": a["domain"], "status": a["status"],
             "position": a["position"], "health": a["health"]} for a in AGENTS_DB.values()]


@router.get("/{agent_id}")
async def get_agent(agent_id: str) -> Dict[str, Any]:
    """Get full agent details for AI inspection."""
    agent = AGENTS_DB.get(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent {agent_id} not found")
    return agent


@router.get("/{agent_id}/explain")
async def explain_agent(agent_id: str) -> Dict[str, Any]:
    """Generate XAI explanation for an agent's recent decisions."""
    agent = AGENTS_DB.get(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent {agent_id} not found")
    return {
        "agent_id": agent_id,
        "current_goal": agent["goals"][0] if agent["goals"] else "unknown",
        "active_planner": agent["planner"],
        "confidence": agent["confidence"],
        "explanation_trace": [
            {"step": i + 1, "decision": d["action"], "why": d["reasoning"],
             "alternatives": d["alternatives"]}
            for i, d in enumerate(agent["decision_history"])
        ],
        "influence_factors": [
            {"factor": "enemy proximity", "weight": 0.8},
            {"factor": "fuel state", "weight": 0.5},
            {"factor": "mission priority", "weight": 0.9},
            {"factor": "asset survivability", "weight": 0.7},
        ],
    }
