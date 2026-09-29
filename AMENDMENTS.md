# Registered Amendments

Both amendments are part of the OSF registration [10.17605/OSF.IO/M398V](https://doi.org/10.17605/OSF.IO/M398V) and were approved before the analysed collection began (28 September 2026, 12:04 UTC).

## Amendment 1 (28 September 2026), registered before any data used in the confirmatory analysis

**What happened.** Data collection started on 28 September 2026 at 05:42 UTC, after registration (05:33 UTC). By 06:32 UTC, 441 trials had been recorded: DeepSeek 249 valid, 183 invalid, 3 missing; Gemini 4 valid, 2 missing. All 183 invalid DeepSeek outputs ended with `finish_reason = length`, and 172 of them had empty content. `deepseek-flash` spends reasoning tokens before it answers, and the registered `max_tokens = 1024` was exhausted before any answer was written. For example, in a post-hoc smoke test on the non-study pilot set, the model used 811 reasoning tokens out of 883 completion tokens. The invalid rate (42%) is far above the 5% threshold declared in Section 8. Collection was stopped. Only operational fields (status, finish reason, HTTP code, latency) were inspected; no hypothesis-related quantity was computed.

**Changes (apply to both models):**
1. `max_tokens` is 4096 instead of 1024. Token usage (`usage`, including reasoning tokens) is logged for every trial.
2. **Invalid-rate gate:** every 100 recorded trials, if a model's cumulative invalid rate exceeds 5%, collection for that model pauses automatically and is not resumed without a further, registered amendment.
3. **Local network failures:** a failure with no HTTP response at all (e.g. DNS/connection loss on the collection machine) is not a property of the model. It is no longer recorded as missing; the run stops and resumes from the same trial. HTTP 5xx responses still count as missing after 5 retries, with a longer exponential backoff (10 s to 120 s).
4. **Restart:** collection restarts from trial 1 of the unchanged schedule (`schedule.jsonl`, same seed and order) into a new file, `results_v2.jsonl`. The 441 trials of the first attempt (`results.jsonl`, SHA-256 `bf03ba316334cd55c37f3e0e86724dd55bd772d5d6f5c1f05858211fa6ad21f4`) are archived, excluded from all confirmatory and exploratory analyses, and reported in the paper as a failed first attempt.
5. **Gemini completion rule:** the free-tier quota of the Gemini API limits the daily number of calls. If the Gemini arm is not complete by **30 November 2026**, it is analysed descriptively only. The confirmatory family then contains the 2 DeepSeek tests, and Holm's correction is applied to that family.

Unchanged: models, prompt, evidence sets, schedule, hypotheses, SESOI, tests, α, TOST bounds, decision criteria, and `analyze.py`.

**Updated frozen hashes** (all other hashes in Section 10 are unchanged):

| File | SHA-256 |
|---|---|
| `common.py` | `7fbd97c12f3883014e062fb2f8729f4bf4bc59fe289d921c0124ff39fa146bb4` |
| `run_trials.py` | `d5f1b0e64ca818d7f75a50db224753a7956c23b7c3aa0a61195f188f3ac742a1` |

---

## Amendment 2 (28 September 2026), registered before any data used in the confirmatory analysis

**What happened.** Collection under Amendment 1 (`max_tokens = 4096`) started on 28 September 2026 at 11:00 UTC. After 100 DeepSeek trials, the invalid-rate gate paused collection: 7 outputs (7%) were invalid. All 7 ended with `finish_reason = length`, used all 4096 tokens as reasoning tokens, and returned empty content. Six of the 7 came from stratum A (balanced conflict) sets.

Among valid DeepSeek outputs, reasoning tokens had a median of 741, a 90th percentile of 2195 and a maximum of 3780. The distribution is heavy-tailed, and the failures concentrate in the most informative stratum, so excluding them would bias the analysis.

For Gemini, the API reported a free-tier limit of 20 requests per day for `gemini-3.8-flash`.

Only operational fields were inspected: status, finish reason, token counts, set id and condition. No hypothesis-related quantity was computed.

**Changes:**

1. `max_tokens = 16384`. A smoke test on the non-study pilot set confirmed that the API accepts this value; that call used 2612 reasoning tokens. The HTTP timeout is 600 s.
2. The invalid-rate gate becomes reporting-only, so collection always runs to completion.
   - Outputs still truncated at 16384 are INVALID, as in the original plan.
   - If the DeepSeek invalid rate exceeds 5%, this is declared as a deviation. The pre-registered sensitivity analysis, which treats INVALID as a fourth output category, is then reported with equal prominence to the primary analysis.
   - The token budget will not be changed again.
3. Collection restarts from trial 1 of the unchanged schedule, writing to `results_v3.jsonl`.
   - The 108 Amendment-1 trials (`results_v2.jsonl`, SHA-256 `93787f4bc285277278cb9b36d6fd77ef0ce51a03d451a6023e54c1645fda6e0e`) are archived and excluded from all analyses.
   - They are reported together with the first attempt as failed attempts.
4. At 20 requests per day, the Gemini arm (3,840 calls) cannot be completed.
   - The confirmatory family is therefore the 2 DeepSeek tests (H1 and H2), and Holm's correction is applied to that family.
   - Gemini data collected up to 30 November 2026 (at most 20 calls per day, in the same schedule order) are reported descriptively only.

**Unchanged:** model `deepseek-flash`, prompt, evidence sets, schedule, hypotheses, SESOI, tests, alpha, TOST bounds, decision criteria and `analyze.py`.

**Updated hashes:**

| File | SHA-256 |
|---|---|
| `common.py` | `9fb4a13b388ffd4c9d5f1e16f6f8bbc41661869a330fc24d3201e26a380f0bd5` |
| `run_trials.py` | `57e1a1d8e4151c1d7e2d53531f0f7a537669b19c639ff5ae6374627d283f84ed` |

All code, seeds and raw logs of all attempts are published with the paper.
