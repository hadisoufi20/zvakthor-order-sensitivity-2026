"""Run the frozen schedule. Resumable: completed trials are skipped, so it can be re-run daily.

Usage (PowerShell):
  $env:DEEPSEEK_API_KEY="..."; $env:GEMINI_API_KEY="..."
  python run_trials.py                 # both models
  python run_trials.py --only gemini   # one model
Keys are read only from the environment and never written to disk.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

from common import (FREEZE_FILE, HERE, MAX_TOKENS, MODELS, RESULTS_FILE, SCHEDULE_FILE, SETS_FILE, TEMPERATURE,
                    build_user_prompt, load_prompt, parse_output, sha256_file)

MIN_INTERVAL_S = {"deepseek": 0.5, "gemini": 4.5}  # stay under free-tier per-minute limits
MAX_RETRIES = 5
TIMEOUT_S = 600  # long reasoning at 16k tokens
INVALID_GATE = 0.05      # Amendment 2: reporting-only warning (no pause); collection always runs to completion
GATE_EVERY = 100


def verify_freeze() -> None:
    if not FREEZE_FILE.exists():
        sys.exit("FREEZE.sha256 missing — run freeze.py first (before any trial).")
    for line in FREEZE_FILE.read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        if sha256_file(HERE / name) != digest:
            sys.exit(f"Frozen file changed after registration: {name}. Refusing to run.")


def call(model_key: str, system: str, user: str, key: str) -> tuple[int, dict]:
    cfg = MODELS[model_key]
    body = {"model": cfg["model"], "temperature": TEMPERATURE, "max_tokens": MAX_TOKENS,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    req = urllib.request.Request(cfg["base"] + "/chat/completions", data=json.dumps(body).encode(), method="POST")
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
            status, text = r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        status, text = e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # network / timeout
        return -1, {"error": f"{type(e).__name__}: {e}"}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return status, {"error": text[:500]}
    # some providers (e.g. Gemini) return error bodies as a JSON list
    if isinstance(payload, list):
        payload = payload[0] if payload and isinstance(payload[0], dict) else {"error": payload}
    return status, payload if isinstance(payload, dict) else {"error": payload}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=list(MODELS))
    ap.add_argument("--max-trials", type=int, default=None, help="stop after N new trials (this run)")
    args = ap.parse_args()

    verify_freeze()
    system, _, _ = load_prompt()
    sets = {s["set_id"]: s for s in json.loads(SETS_FILE.read_text(encoding="utf-8"))["sets"]}
    done = set()
    if RESULTS_FILE.exists():
        for line in RESULTS_FILE.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            if rec["status"] in ("ok", "invalid", "missing"):
                done.add(rec["trial_id"])

    keys = {m: os.getenv(c["env"], "").strip() for m, c in MODELS.items()}
    active = {m for m in MODELS if keys[m] and (args.only in (None, m))}
    if not active:
        sys.exit("No API key set for the selected model(s).")
    paused: set[str] = set()
    counts = {m: [0, 0] for m in MODELS}  # [recorded, invalid] for the invalid-rate gate (whole results file)
    if RESULTS_FILE.exists():
        for line in RESULTS_FILE.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            counts[rec["model"]][0] += 1
            counts[rec["model"]][1] += rec["status"] == "invalid"
    last_call = {m: 0.0 for m in MODELS}
    new = 0

    with RESULTS_FILE.open("a", encoding="utf-8", newline="\n") as out:
        for line in SCHEDULE_FILE.read_text(encoding="utf-8").splitlines():
            t = json.loads(line)
            m = t["model"]
            if t["trial_id"] in done or m not in active or m in paused:
                continue
            if args.max_trials is not None and new >= args.max_trials:
                break
            user = build_user_prompt(sets[t["set_id"]]["votes"], t["order"])
            prompt_sha = hashlib.sha256((system + "\n\n" + user).encode()).hexdigest()
            status, payload, attempts = -1, {}, 0
            while attempts < MAX_RETRIES:
                wait = MIN_INTERVAL_S[m] - (time.monotonic() - last_call[m])
                if wait > 0:
                    time.sleep(wait)
                t0 = time.perf_counter()
                status, payload = call(m, system, user, keys[m])
                latency = round((time.perf_counter() - t0) * 1000)
                last_call[m] = time.monotonic()
                attempts += 1
                if status == 200:
                    break
                time.sleep(min(120, 5 * 2 ** attempts))
            rec = {"trial_id": t["trial_id"], "model": m, "set_id": t["set_id"], "condition": t["condition"],
                   "rep": t["rep"], "order": t["order"], "prompt_sha256": prompt_sha,
                   "requested_model": MODELS[m]["model"], "attempts": attempts,
                   "utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            if status == 200:
                choice = (payload.get("choices") or [{}])[0]
                raw = (choice.get("message") or {}).get("content")
                parsed = parse_output(raw)
                rec.update(status="ok" if parsed else "invalid", http_status=status, latency_ms=latency,
                           returned_model=payload.get("model"), system_fingerprint=payload.get("system_fingerprint"),
                           finish_reason=choice.get("finish_reason"), raw=raw,
                           response_sha256=hashlib.sha256((raw or "").encode()).hexdigest(),
                           usage=payload.get("usage"),
                           direction=parsed["direction"] if parsed else None,
                           confidence=parsed["confidence"] if parsed else None)
            elif status == -1:
                # Amendment 1: no HTTP response at all (local network/DNS) is not a model property -> not recorded;
                # the run stops and resumes from this trial next time.
                print(f"[{m}] network unreachable after {attempts} attempts: {payload.get('error')} — stopping; re-run later.")
                break
            elif status == 429:
                # quota exhausted: not a lost trial — pause this model, resume in a later run
                paused.add(m)
                print(f"[{m}] rate limit / quota reached — paused; re-run later to resume.")
                continue
            else:
                rec.update(status="missing", http_status=status, error=payload.get("error") if isinstance(payload, dict) else None)
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out.flush()
            new += 1
            counts[m][0] += 1
            counts[m][1] += rec["status"] == "invalid"
            if counts[m][0] % GATE_EVERY == 0 and counts[m][1] / counts[m][0] > INVALID_GATE:
                print(f"[{m}] note: invalid rate {counts[m][1]}/{counts[m][0]} (> {INVALID_GATE:.0%}) — continuing (Amendment 2).")
            if new % 50 == 0:
                print(f"{new} new trials recorded")
    total = sum(1 for _ in SCHEDULE_FILE.open(encoding="utf-8"))
    print(f"run finished: {new} new trials this run; {len(done) + new}/{total} total")
    for mm, (n_rec, n_inv) in counts.items():
        print(f"  {mm}: {n_rec} recorded, {n_inv} invalid")


if __name__ == "__main__":
    main()
