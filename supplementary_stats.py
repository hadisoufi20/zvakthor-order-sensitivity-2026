"""Supplementary descriptive statistics for the paper (NOT part of the registered analysis).
Reads results_v3.jsonl, evidence_sets.json and analysis_report.json; prints every descriptive number
reported in the paper that analyze.py does not produce. Deterministic (bootstrap seed 1, 20,000 resamples)."""
from __future__ import annotations

import collections
import json
import statistics

import numpy as np

from common import HERE, RESULTS_FILE, SETS_FILE, WEIGHTS_2026_09_26, aggregate

DIRS = ("BUY", "SELL", "NEUTRAL")
L = [json.loads(l) for l in RESULTS_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
ok = [r for r in L if r["status"] == "ok"]
sets = {s["set_id"]: s for s in json.loads(SETS_FILE.read_text(encoding="utf-8"))["sets"]}
per_set = json.loads((HERE / "analysis_report.json").read_text(encoding="utf-8"))["models"]["deepseek"]["H1"]["per_set"]
out = {}

d = np.array([per_set[k]["D_P"] - per_set[k]["D_R"] for k in sorted(per_set)])
rng = np.random.default_rng(1)
boot = [rng.choice(d, d.size).mean() for _ in range(20_000)]
out["bootstrap95_mean_dD"] = [float(x) for x in np.percentile(boot, [2.5, 97.5])]
out["sign_counts_dD"] = {"pos": int((d > 0).sum()), "zero": int((d == 0).sum()), "neg": int((d < 0).sum())}
out["mean_dD_strata_AB"] = float(np.mean([per_set[k]["D_P"] - per_set[k]["D_R"] for k in per_set if k[0] in "AB"]))

strata = {}
for s in "ABC":
    ks = [k for k in per_set if k[0] == s]
    modal = []
    for k in ks:
        R = [r["direction"] for r in ok if r["set_id"] == k and r["condition"] == "R"]
        modal.append(collections.Counter(R).most_common(1)[0][1] / len(R))
    reason = [(r.get("usage") or {}).get("completion_tokens_details", {}).get("reasoning_tokens", 0)
              for r in L if r["set_id"][0] == s]
    strata[s] = {"mean_D_P": float(np.mean([per_set[k]["D_P"] for k in ks])),
                 "mean_D_R": float(np.mean([per_set[k]["D_R"] for k in ks])),
                 "mean_dD": float(np.mean([per_set[k]["D_P"] - per_set[k]["D_R"] for k in ks])),
                 "R_modal_share_mean": float(np.mean(modal)), "R_modal_share_min": float(min(modal)),
                 "median_reasoning_tokens_all_calls": float(np.median(reason))}
out["strata"] = strata

tvd, counts = {}, {}
for k in sorted(sets):
    P = [r["direction"] if r["status"] == "ok" else "INVALID" for r in L if r["set_id"] == k and r["condition"] == "P"]
    R = [r["direction"] if r["status"] == "ok" else "INVALID" for r in L if r["set_id"] == k and r["condition"] == "R"]
    cats = DIRS + ("INVALID",)
    tvd[k] = 0.5 * sum(abs(P.count(c) / len(P) - R.count(c) / len(R)) for c in cats)
    counts[k] = {"P": dict(collections.Counter(P)), "R": dict(collections.Counter(R))}
def _gs(lab, cats):
    n = len(lab)
    return n / (n - 1) * (1 - sum((lab.count(c) / n) ** 2 for c in cats))
out["sensitivity_mean_dD_invalid_as_4th_category"] = float(np.mean(
    [_gs(counts_P, DIRS + ("INVALID",)) - _gs(counts_R, DIRS + ("INVALID",)) for counts_P, counts_R in
     [([r["direction"] if r["status"] == "ok" else "INVALID" for r in L if r["set_id"] == k and r["condition"] == "P"],
       [r["direction"] if r["status"] == "ok" else "INVALID" for r in L if r["set_id"] == k and r["condition"] == "R"])
      for k in sorted(sets)]]))
out["tvd_P_vs_R"] = {"mean_by_stratum": {s: float(np.mean([v for k, v in tvd.items() if k[0] == s])) for s in "ABC"},
                     "per_set": tvd}
out["direction_counts"] = counts

ct = [r["usage"]["completion_tokens"] for r in L]
out["completion_tokens_all_calls"] = {"median": float(np.median(ct)), "p90": float(np.percentile(ct, 90))}
out["raw_responses_all_distinct"] = len({r["response_sha256"] for r in L}) == len(L)
out["conf_mean"] = {c: float(np.mean([r["confidence"] for r in ok if r["condition"] == c])) for c in "PR"}
out["returned_models"] = dict(collections.Counter(r.get("returned_model") for r in L))
out["fingerprints"] = dict(collections.Counter(r.get("system_fingerprint") for r in L))

# H3 decomposition: where decisions can change, and why
reach, flips = {}, collections.Counter()
for k, s in sets.items():
    base = [(a, v["direction"], v["confidence"]) for a, v in s["votes"].items()]
    reach[k] = sorted({str(aggregate(base + [("research", dd, c / 100)], WEIGHTS_2026_09_26))
                       for dd in DIRS for c in range(101)})
    reps = [r for r in ok if r["set_id"] == k and r["condition"] == "R"]
    mode = collections.Counter(r["direction"] for r in reps).most_common(1)[0][0]
    ref = aggregate(base + [("research", mode, statistics.median(r["confidence"] for r in reps if r["direction"] == mode))],
                    WEIGHTS_2026_09_26)
    for r in ok:
        if r["set_id"] == k and aggregate(base + [("research", r["direction"], r["confidence"])], WEIGHTS_2026_09_26) != ref:
            flips[(k, r["condition"], "direction" if r["direction"] != mode else "confidence")] += 1
out["h3_sets_where_consensus_reachable"] = [k for k, v in reach.items() if len(v) > 1]
out["h3_changes_by_set_condition_cause"] = {"|".join(k): v for k, v in flips.items()}


# ---- failed attempts (archived logs; excluded from all analyses)
att = {}
for name, alt in (("archived_v1_results.jsonl", "results_v1.jsonl"), ("archived_v2_results.jsonl", "results_v2.jsonl")):
    f = HERE / name if (HERE / name).exists() else HERE / alt
    if not f.exists():
        raise SystemExit(f"missing archived log: {name} (or {alt})")
    A = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    inv = [r for r in A if r["status"] == "invalid"]
    att[name] = {"n": len(A), "window_utc": [A[0]["utc"], A[-1]["utc"]],
                 "status_by_model": {f"{m}:{s}": n for (m, s), n in collections.Counter((r["model"], r["status"]) for r in A).items()},
                 "invalid_empty": sum(1 for r in inv if not r.get("raw")), "invalid_with_text": sum(1 for r in inv if r.get("raw")),
                 "invalid_by_stratum": dict(collections.Counter(r["set_id"][0] for r in inv))}
out["failed_attempts"] = att

# ---- Holm under the originally registered four-test family (bounds; Gemini tests never run)
p1 = json.loads((HERE / "analysis_report.json").read_text(encoding="utf-8"))["models"]["deepseek"]["H1"]["p_one_sided"]
out["holm_4family_H1_lower_bound"] = 3 * p1
out["holm_4family_H1_if_smallest"] = 4 * p1
print(json.dumps(out, indent=1))
