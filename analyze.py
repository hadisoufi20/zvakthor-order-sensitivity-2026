"""Pre-registered analysis (H1, H2, H3 + TOST + Holm + exploratory). Deterministic (seeded)."""
from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict

import numpy as np

from common import (HERE, MODELS, RESULTS_FILE, SETS_FILE, WEIGHTS_2026_09_26,
                    WEIGHTS_CURRENT, aggregate)

N_PERM = 10_000
SEED = 20261003
SESOI = 0.05
TOST_BOUND = 0.02
ALPHA = 0.05
DIRS = ("BUY", "SELL", "NEUTRAL")


def gini_simpson(labels: list[str]) -> float:
    n = len(labels)
    if n < 2:
        return float("nan")
    p = np.array([labels.count(d) / n for d in DIRS])
    return n / (n - 1) * (1 - float((p ** 2).sum()))


def signflip_p(d: np.ndarray, rng, alternative: str) -> float:
    obs = d.mean()
    signs = rng.choice([-1.0, 1.0], size=(N_PERM, d.size))
    null = (signs * d).mean(axis=1)
    if alternative == "greater":
        return float((np.sum(null >= obs) + 1) / (N_PERM + 1))
    return float((np.sum(null <= obs) + 1) / (N_PERM + 1))


def holm(pvals: dict) -> dict:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, out, running = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        out[k] = running
    return out


def main() -> None:
    rng = np.random.default_rng(SEED)
    sets = {s["set_id"]: s for s in json.loads(SETS_FILE.read_text(encoding="utf-8"))["sets"]}
    recs = [json.loads(l) for l in RESULTS_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    report = {"n_records": len(recs), "models": {}}
    raw_p = {}

    for model in MODELS:
        R = [r for r in recs if r["model"] == model]
        ok = [r for r in R if r["status"] == "ok"]
        mr = {"counts": dict(Counter(f"{r['condition']}:{r['status']}" for r in R)),
              "returned_models": dict(Counter(r.get("returned_model") for r in R if r["status"] != "missing"))}

        # ---- H1: Gini-Simpson(P) - Gini-Simpson(R), per set; sign-flip permutation, one-sided
        by = defaultdict(lambda: {"P": [], "R": []})
        for r in ok:
            by[r["set_id"]][r["condition"]].append(r["direction"])
        deltas, per_set = [], {}
        for sid in sorted(sets):
            dP, dR = gini_simpson(by[sid]["P"]), gini_simpson(by[sid]["R"])
            per_set[sid] = {"D_P": dP, "D_R": dR, "n_P": len(by[sid]["P"]), "n_R": len(by[sid]["R"])}
            if not (np.isnan(dP) or np.isnan(dR)):
                deltas.append(dP - dR)
        d = np.array(deltas)
        if d.size:
            p1 = signflip_p(d, rng, "greater")
            p_lo = signflip_p(d + TOST_BOUND, rng, "greater")
            p_hi = signflip_p(d - TOST_BOUND, rng, "less")
            mr["H1"] = {"n_sets": int(d.size), "mean_delta": float(d.mean()), "p_one_sided": p1,
                        "tost_p": max(p_lo, p_hi), "per_set": per_set,
                        "by_stratum_mean_delta": {s: float(np.mean([per_set[k]["D_P"] - per_set[k]["D_R"]
                                                                   for k in per_set if k.startswith(s)]))
                                                  for s in "ABC"}}
            raw_p[f"H1_{model}"] = p1

        # ---- H2: position of output-agreeing vs disagreeing votes (strata A, B; P trials; BUY/SELL outputs)
        stats_by_set = defaultdict(list)  # per trial: (stat_if_BUY, stat_if_SELL, observed_label)
        for r in ok:
            if r["condition"] != "P" or r["set_id"][0] not in "AB" or r["direction"] not in ("BUY", "SELL"):
                continue
            votes = sets[r["set_id"]]["votes"]
            pos = {a: i + 1 for i, a in enumerate(r["order"])}
            def stat(out):
                agree = [pos[a] for a, v in votes.items() if v["direction"] == out]
                dis = [pos[a] for a, v in votes.items() if v["direction"] != out]
                return statistics.mean(agree) - statistics.mean(dis)
            stats_by_set[r["set_id"]].append((stat("BUY"), stat("SELL"), 0 if r["direction"] == "BUY" else 1))
        if stats_by_set:
            arrs = [(np.array([x[0] for x in tr]), np.array([x[1] for x in tr]), np.array([x[2] for x in tr]))
                    for tr in stats_by_set.values()]
            n_tr = sum(a[2].size for a in arrs)
            obs = float(sum(np.where(lbl == 0, sb, ss).sum() for sb, ss, lbl in arrs) / n_tr)
            null = np.zeros(N_PERM)
            for sb, ss, lbl in arrs:
                perms = np.array([rng.permutation(lbl) for _ in range(N_PERM)])
                null += np.where(perms == 0, sb, ss).sum(axis=1)
            null /= n_tr
            p2 = float((np.sum(np.abs(null - null.mean()) >= abs(obs - null.mean())) + 1) / (N_PERM + 1))
            mr["H2"] = {"n_trials": int(n_tr), "mean_position_gap": obs,
                        "null_mean": float(null.mean()), "p_two_sided": p2,
                        "interpretation": "negative = primacy, positive = recency"}
            raw_p[f"H2_{model}"] = p2

        # ---- H3: decision impact through the production aggregator (descriptive)
        h3 = {}
        for label, weights in (("weights_2026_09_26", WEIGHTS_2026_09_26), ("weights_current", WEIGHTS_CURRENT)):
            flips, n, rflips, rn = 0, 0, 0, 0
            for sid, s in sets.items():
                base_votes = [(a, v["direction"], v["confidence"]) for a, v in s["votes"].items()]
                reps = [r for r in ok if r["set_id"] == sid and r["condition"] == "R"]
                if not reps:
                    continue
                mode = Counter(r["direction"] for r in reps).most_common(1)[0][0]
                ref_conf = statistics.median(r["confidence"] for r in reps if r["direction"] == mode)
                ref = aggregate(base_votes + [("research", mode, ref_conf)], weights)
                for r in ok:
                    if r["set_id"] != sid:
                        continue
                    changed = aggregate(base_votes + [("research", r["direction"], r["confidence"])], weights) != ref
                    if r["condition"] == "P":
                        n, flips = n + 1, flips + changed
                    else:
                        rn, rflips = rn + 1, rflips + changed
            h3[label] = {"n_trials": n, "decision_flip_rate": flips / n if n else None,
                         "noise_baseline_flip_rate_R": rflips / rn if rn else None,
                         "order_attributable_flip_rate": (flips / n - rflips / rn) if n and rn else None}
        mr["H3"] = h3

        # ---- exploratory
        mr["exploratory"] = {
            "invalid_rate": {c: (sum(1 for r in R if r["condition"] == c and r["status"] == "invalid") /
                                 max(1, sum(1 for r in R if r["condition"] == c and r["status"] != "missing")))
                             for c in ("P", "R")},
            "confidence_sd": {c: float(np.std([r["confidence"] for r in ok if r["condition"] == c]))
                              if any(r["condition"] == c for r in ok) else None for c in ("P", "R")},
        }
        report["models"][model] = mr

    report["holm_adjusted"] = holm(raw_p) if raw_p else {}
    report["decisions"] = {}
    for model, mr in report["models"].items():
        if "H1" not in mr:
            continue
        h1_sig = report["holm_adjusted"].get(f"H1_{model}", 1) < ALPHA
        verdict = ("order-sensitive" if h1_sig and mr["H1"]["mean_delta"] >= SESOI else
                   "equivalent-to-noise" if mr["H1"]["tost_p"] < ALPHA else "inconclusive")
        report["decisions"][model] = verdict
    (HERE / "analysis_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"holm_adjusted": report["holm_adjusted"], "decisions": report["decisions"],
                      "H3": {m: v.get("H3") for m, v in report["models"].items()}}, indent=2))


if __name__ == "__main__":
    main()
