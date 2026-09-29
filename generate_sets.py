"""Generate the 24 frozen synthetic evidence sets (3 strata x 8). Deterministic (seeded)."""
from __future__ import annotations

import json
import random

from common import AGENTS, SETS_FILE

SEED = 20261001

REASONS = {
    "regime": {"BUY": "H1 uptrend, ADX {x}, price above EMA50",
               "SELL": "H1 downtrend, ADX {x}, price below EMA50",
               "NEUTRAL": "H1 range-bound, ADX {x}, no directional regime"},
    "ml_structure": {"BUY": "bullish structure: spring confirmed, composite score {x}",
                     "SELL": "bearish structure: upthrust confirmed, composite score {x}",
                     "NEUTRAL": "mixed structure, composite score {x}"},
    "correlation": {"BUY": "DXY weakening {x}% with risk-on equities",
                    "SELL": "DXY strengthening {x}% with risk-off equities",
                    "NEUTRAL": "cross-asset moves flat ({x}%), no clear driver"},
    "fundamental": {"BUY": "positive surprise index {x} on latest releases",
                    "SELL": "negative surprise index {x} on latest releases",
                    "NEUTRAL": "surprise index {x}, releases in line with consensus"},
    "sentiment": {"BUY": "news sentiment positive (score {x})",
                  "SELL": "news sentiment negative (score {x})",
                  "NEUTRAL": "news sentiment balanced (score {x})"},
}


def _detail(rng: random.Random, agent: str) -> str:
    return {"regime": lambda: str(rng.randint(18, 34)),
            "ml_structure": lambda: f"{rng.uniform(0.55, 0.8):.2f}",
            "correlation": lambda: f"{rng.uniform(0.1, 0.6):.2f}",
            "fundamental": lambda: f"{rng.uniform(0.2, 1.5):.2f}",
            "sentiment": lambda: f"{rng.uniform(0.2, 0.7):.2f}"}[agent]()


def _make_set(rng: random.Random, set_id: str, stratum: str, directions: list[str], conf_ranges: list[tuple]) -> dict:
    agents = AGENTS[:]
    rng.shuffle(agents)  # which agent gets which direction is random
    votes = {}
    for agent, d, (lo, hi) in zip(agents, directions, conf_ranges):
        votes[agent] = {"direction": d, "confidence": round(rng.uniform(lo, hi), 2), "quality": "real",
                        "reason": REASONS[agent][d].format(x=_detail(rng, agent))}
    return {"set_id": set_id, "stratum": stratum, "votes": votes}


def main() -> None:
    rng = random.Random(SEED)
    sets = []
    for i in range(8):  # A: balanced conflict — 2 BUY, 2 SELL, 1 NEUTRAL, close confidences
        base = rng.uniform(0.55, 0.72)
        sets.append(_make_set(rng, f"A{i+1:02d}", "A_balanced_conflict", ["BUY", "BUY", "SELL", "SELL", "NEUTRAL"],
                              [(base - .03, base + .03)] * 4 + [(0.40, 0.60)]))
    for i in range(8):  # B: weak majority 3 vs 2
        maj, mino = ("BUY", "SELL") if i % 2 == 0 else ("SELL", "BUY")
        base = rng.uniform(0.55, 0.70)
        sets.append(_make_set(rng, f"B{i+1:02d}", "B_weak_majority", [maj] * 3 + [mino] * 2,
                              [(base - .05, base + .05)] * 5))
    for i in range(8):  # C: clear consensus (control) — 4+1 NEUTRAL or 5 aligned
        d = "BUY" if i % 2 == 0 else "SELL"
        dirs = [d] * 5 if i < 4 else [d] * 4 + ["NEUTRAL"]
        sets.append(_make_set(rng, f"C{i+1:02d}", "C_clear_consensus", dirs, [(0.65, 0.85)] * 5))
    SETS_FILE.write_text(json.dumps({"seed": SEED, "sets": sets}, indent=2), encoding="utf-8", newline="\n")
    print(f"wrote {len(sets)} sets -> {SETS_FILE.name}")


if __name__ == "__main__":
    main()
