"""Technical smoke test — NOT study data. Uses one evidence set that is not part of the study (declared in the
pre-registration: at most 5 calls per model). Checks connectivity, JSON mode and the parser. Writes nothing."""
from __future__ import annotations

import json
import os
import sys

from common import MODELS, build_user_prompt, load_prompt, parse_output
from run_trials import call

PILOT_VOTES = {  # fixed, outside the 24 study sets
    "correlation": {"direction": "BUY", "confidence": 0.61, "quality": "real", "reason": "pilot only"},
    "fundamental": {"direction": "BUY", "confidence": 0.55, "quality": "real", "reason": "pilot only"},
    "ml_structure": {"direction": "SELL", "confidence": 0.58, "quality": "real", "reason": "pilot only"},
    "regime": {"direction": "BUY", "confidence": 0.70, "quality": "real", "reason": "pilot only"},
    "sentiment": {"direction": "NEUTRAL", "confidence": 0.50, "quality": "real", "reason": "pilot only"},
}

if __name__ == "__main__":
    system, _, _ = load_prompt()
    user = build_user_prompt(PILOT_VOTES, sorted(PILOT_VOTES))
    ok_all = True
    for m, cfg in MODELS.items():
        key = os.getenv(cfg["env"], "").strip()
        if not key:
            print(f"{m:<9} NO KEY"); ok_all = False; continue
        status, payload = call(m, system, user, key)
        choice = (payload.get("choices") or [{}])[0] if status == 200 else {}
        raw = (choice.get("message") or {}).get("content")
        parsed = parse_output(raw)
        print(f"{m:<9} http={status} returned_model={payload.get('model')} finish={choice.get('finish_reason')} parsed={parsed}")
        print(f"          usage={payload.get('usage')}")
        if not parsed:
            ok_all = False
            print("   detail:", (raw or json.dumps(payload, ensure_ascii=False))[:600])
    sys.exit(0 if ok_all else 1)
