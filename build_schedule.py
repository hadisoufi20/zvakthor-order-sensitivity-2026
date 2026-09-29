"""Build the frozen, randomized, interleaved trial schedule. Deterministic (seeded)."""
from __future__ import annotations

import itertools
import json
import random

from common import AGENTS, CANONICAL_ORDER, MODELS, SCHEDULE_FILE, SETS_FILE

SEED = 20261002
N_REPEATS = 40


def main() -> None:
    sets = json.loads(SETS_FILE.read_text(encoding="utf-8"))["sets"]
    perms = list(itertools.permutations(sorted(AGENTS)))
    assert len(perms) == 120
    trials = []
    for model in MODELS:
        for s in sets:
            for k, p in enumerate(perms):
                trials.append({"model": model, "set_id": s["set_id"], "condition": "P", "rep": k, "order": list(p)})
            for r in range(N_REPEATS):
                trials.append({"model": model, "set_id": s["set_id"], "condition": "R", "rep": r, "order": CANONICAL_ORDER})
    random.Random(SEED).shuffle(trials)
    with SCHEDULE_FILE.open("w", encoding="utf-8", newline="\n") as f:
        for i, t in enumerate(trials):
            t["trial_id"] = f"T{i:05d}"
            f.write(json.dumps(t) + "\n")
    print(f"wrote {len(trials)} trials -> {SCHEDULE_FILE.name}")


if __name__ == "__main__":
    main()
