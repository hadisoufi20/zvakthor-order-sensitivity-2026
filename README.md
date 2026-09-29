# Order Invariance at the Last Language-Model Boundary

This repository contains the materials, code and data for a pre-registered test of order sensitivity. The test targets the LLM evidence synthesizer (Research agent) of the ZVAKTHOR multi-agent trading architecture.

**Paper:** Soufi, H. (2026). *Order Invariance at the Last Language-Model Boundary: A Pre-Registered Test of an LLM Evidence Synthesizer Inside a Deterministic Trading Architecture.*

**Pre-registration:** OSF Registries, [DOI 10.17605/OSF.IO/M398V](https://doi.org/10.17605/OSF.IO/M398V). Registered 28 September 2026, 05:33 UTC, with Amendments 1 and 2 (see `AMENDMENTS.md`).

## What was tested

- **Model:** `deepseek-flash`, temperature 0, JSON mode, `max_tokens` = 16,384.
- **Prompt:** the production prompt of the Research agent.
- **Input:** 24 synthetic evidence sets of five agent votes, in three strata:
  - A: balanced conflict
  - B: weak majority
  - C: clear consensus
- **Conditions:** each set was run under two conditions.
  - **P:** all 120 orderings of the votes.
  - **R:** one fixed canonical ordering, repeated 40 times. This measures intrinsic noise.
- **Volume:** 3,840 calls in total.

## Files

All files sit in one folder, because the scripts resolve paths relative to their own location.

| File | Role |
|---|---|
| `PreRegistration_OrderSensitivity_EN.md` | Registered plan, including Section 12 (Amendment 1), exactly as uploaded to OSF |
| `AMENDMENTS.md` | Amendments 1 and 2, as registered on OSF |
| `research_prompt_snapshot.txt` | Frozen production prompt |
| `generate_sets.py` / `evidence_sets.json` | Seeded generator (seed 20261001) and the 24 evidence sets |
| `build_schedule.py` / `schedule.jsonl` | Seeded, randomly interleaved trial schedule (seed 20261002) |
| `common.py` | Shared definitions and the exact replica of the production aggregation rule |
| `run_trials.py` | Collection harness; verifies `FREEZE.sha256` before every run |
| `smoke_test.py` | Connectivity check on a non-study evidence set |
| `freeze.py` / `FREEZE.sha256` | SHA-256 hashes of every file that defines the study |
| `analyze.py` | Registered analysis: H1, H2, H3, TOST and Holm (seed 20261003) |
| `supplementary_stats.py` | Descriptive statistics reported in the paper; not part of the registered analysis |
| `results_v3.jsonl` | **Analysed data:** 3,840 trials, 28 Sep 2026, 12:04–23:57 UTC |
| `archived_v1_results.jsonl` | First attempt (`max_tokens` = 1,024; 441 trials); archived and excluded |
| `archived_v2_results.jsonl` | Second attempt (`max_tokens` = 4,096; 108 trials); archived and excluded |
| `analysis_report.json` | Output of `analyze.py` |
| `supplementary_stats.json` | Output of `supplementary_stats.py` |

## Reproduce the results

Requires Python 3.10+ and `numpy`. No API key is needed.

```bash
pip install numpy
sha256sum -c FREEZE.sha256                            # verify frozen files
python analyze.py                                     # regenerates analysis_report.json
python supplementary_stats.py > supplementary_stats.json
```

Both scripts are deterministic, so their outputs should match the committed JSON files exactly.

## Integrity

| File | SHA-256 |
|---|---|
| `results_v3.jsonl` | `b2745021b8e5c991f2bda4f382986016c1c06332568436bc750cb95e925f5479` |
| `archived_v1_results.jsonl` | `bf03ba316334cd55c37f3e0e86724dd55bd772d5d6f5c1f05858211fa6ad21f4` |
| `archived_v2_results.jsonl` | `93787f4bc285277278cb9b36d6fd77ef0ce51a03d451a6023e54c1645fda6e0e` |

API keys were read only from environment variables, and they never appear in any file or log.

## Re-running data collection (optional)

Collection calls the paid DeepSeek API and will not reproduce the logs byte for byte, because the API is nondeterministic at temperature 0; that is one of the paper's findings.

```bash
export DEEPSEEK_API_KEY=...        # never commit keys
python run_trials.py --only deepseek
```

## Results in brief

- **H1:** the mean diversity increase under permutation is 0.028. Holm-adjusted p = 0.042 within the amended two-test family. The point estimate is below the SESOI of 0.05, but the 95% interval includes it. Pre-registered verdict: **inconclusive**.
- **H2:** no evidence of a primacy or recency effect (p = 0.49).
- **Intrinsic noise:** under an identical input, the modal direction is returned in 72.2% of repeats in the balanced-conflict stratum.
- **H3:** no change in output direction altered any consensus result. All 43 consensus changes arose from confidence variation in a single near-threshold set.

See the paper for the full results, the deviations from the plan, and the limitations.

## Licence

- **Code:** MIT (see `LICENSE`).
- **Data and documents:** CC BY 4.0.

## Conflict of interest

The author designed the system under test.
