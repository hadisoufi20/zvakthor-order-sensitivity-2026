"""Shared definitions for the pre-registered order-sensitivity study (ZVAKTHOR ResearchAgent)."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROMPT_FILE = HERE / "research_prompt_snapshot.txt"
SETS_FILE = HERE / "evidence_sets.json"
SCHEDULE_FILE = HERE / "schedule.jsonl"
RESULTS_FILE = HERE / "results_v3.jsonl"  # archived: results.jsonl (v1, 1024) and results_v2.jsonl (v2, 4096); see Amendments 1-2
FREEZE_FILE = HERE / "FREEZE.sha256"

AGENTS = ["regime", "ml_structure", "correlation", "fundamental", "sentiment"]
CANONICAL_ORDER = sorted(AGENTS)  # alphabetical by agent_type value (task P4, mitigation M1)
DIRECTIONS = ("BUY", "SELL", "NEUTRAL")

MODELS = {
    "deepseek": {"base": "https://api.deepseek.com", "model": "deepseek-flash", "env": "DEEPSEEK_API_KEY"},
    "gemini": {"base": "https://generativelanguage.googleapis.com/v1beta/openai", "model": "gemini-3.8-flash", "env": "GEMINI_API_KEY"},
}
TEMPERATURE = 0
MAX_TOKENS = 16384  # Amendment 2: 4096 still truncated 7% of DeepSeek outputs (reasoning-only, stratum A)

# Production weights as of 2026-09-26 (governance.toml [agent_weights]) — used only for H3.
WEIGHTS_2026_09_26 = {"fundamental": 0.6, "regime": 1.0, "sentiment": 0.7, "research": 1.0,
                      "correlation": 0.5, "ml_structure": 0.9}
WEIGHTS_CURRENT = dict(WEIGHTS_2026_09_26, research=0.0)
CONSENSUS_THRESHOLD = 0.5


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_prompt() -> tuple[str, str, str]:
    text = PROMPT_FILE.read_text(encoding="utf-8")
    grab = lambda tag: re.search(rf"<<<{tag}\n(.*?)\n{tag}>>>", text, re.S).group(1)
    return grab("SYSTEM_PROMPT"), grab("USER_PROMPT_HEADER"), grab("EVIDENCE_LINE")


def build_user_prompt(votes_by_agent: dict, order: list[str]) -> str:
    _, header, line_fmt = load_prompt()
    lines = [line_fmt.format(agent_type=a, **votes_by_agent[a]) for a in order]
    return header + "\n" + "\n".join(lines)


def parse_output(raw: str | None) -> dict | None:
    """Mirror of StructuredResearchOutput validation. Returns None when invalid."""
    if not raw:
        return None
    s = raw.strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s)
    try:
        obj = json.loads(s)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    d, c, syn = obj.get("direction"), obj.get("confidence"), obj.get("synthesis")
    if d not in DIRECTIONS or not isinstance(c, (int, float)) or isinstance(c, bool) or not 0 <= c <= 1:
        return None
    if not isinstance(syn, str) or len(syn) < 10:
        return None
    return {"direction": d, "confidence": float(c)}


def aggregate(votes: list[tuple[str, str, float]], weights: dict) -> tuple[str, bool]:
    """Exact replica of AgentCoordinator.aggregate (agents_v2, 2026-09-27). votes: (agent, direction, confidence)."""
    scores = {"BUY": 0.0, "SELL": 0.0, "NEUTRAL": 0.0}
    total = 0.0
    for agent, direction, conf in votes:
        w = weights.get(agent, 0.0) * conf
        if w <= 0.0 or (agent == "regime" and direction == "NEUTRAL"):
            continue
        scores[direction] += w
        total += w
    if total == 0.0 or (scores["BUY"] == 0.0 and scores["SELL"] == 0.0):
        return "NEUTRAL", False
    win = "BUY" if scores["BUY"] >= scores["SELL"] else "SELL"
    opp = "SELL" if win == "BUY" else "BUY"
    margin = (scores[win] - scores[opp]) / total
    reached = margin >= CONSENSUS_THRESHOLD
    return (win if reached else "NEUTRAL"), reached
