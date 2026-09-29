"""Write FREEZE.sha256 — SHA-256 of every file that defines the study. Run once, before the first trial.
The hashes are copied into the OSF pre-registration; run_trials.py refuses to run if any file changes."""
from common import FREEZE_FILE, HERE, sha256_file

FROZEN = ["research_prompt_snapshot.txt", "evidence_sets.json", "schedule.jsonl",
          "common.py", "generate_sets.py", "build_schedule.py", "run_trials.py", "analyze.py"]

if __name__ == "__main__":
    lines = [f"{sha256_file(HERE / n)}  {n}" for n in FROZEN]
    FREEZE_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))
