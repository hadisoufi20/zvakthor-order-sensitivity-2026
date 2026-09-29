# Order Sensitivity of an LLM Evidence Synthesizer Inside a Deterministic Trading Architecture: A Pre-Registered Test

**Author:** Hadi Soufi — Independent Researcher; Founder, ZVAKTHOR
**Registry:** OSF Registries (OSF Preregistration template)
**Pre-registration version:** 2

**Data status at registration.** No data from the main study have been collected. Two technical steps were performed before registration, and neither is used in any analysis:
1. An API access check: one call per model, with the unrelated prompt `{"ok": true}`.
2. A smoke test: at most 5 calls per model, on one fixed evidence set that is not among the 24 study sets (`smoke_test.py`).

**Change from version 1.** A code review showed that no LLM in ZVAKTHOR selects among multiple recommendations; vote aggregation is deterministic and order-invariant. The only point at which an LLM reads an ordered input is the Research agent. This version targets that real component.

---

## 1. Motivation and research questions

In the ZVAKTHOR architecture, the Research agent — the only LLM-based component — receives the votes of five other agents as an ordered text list and returns a directional vote (BUY/SELL/NEUTRAL) with a confidence value. Until 27 September 2026 this vote entered the consensus with weight 1.0. On 27 September 2026, a recorded architectural decision set its weight to zero (Stage 0); implementation of that decision in code is in progress.

The literature shows that LLMs are sensitive to input order (Liu et al., 2023; Zheng et al., 2024; Wadi & Ma, 2026; Bito et al., 2026). This sensitivity has not been measured inside a real trading system, using the production prompt and format, together with its effect on the final decision.

**Research questions**

1. Is the Research agent's output sensitive to the order of the evidence, **beyond the model's own intrinsic noise**?
2. Does the list position (first or last) of votes that agree with the output differ systematically?
3. Had the Research agent kept its former weight of 1.0, what share of consensus decisions would this sensitivity have changed?

## 2. System under test

- **Prompt:** exactly the `SYSTEM_PROMPT` and evidence-line format in `agents_v2/nexus_ai_agents/research_agent.py` (production version, 27 September 2026), snapshotted in `research_prompt_snapshot.txt`. SHA-256: `c76f4009a870fcd6802a13498178c5fe23201fbb1c39ff33e1b09b693c4ee3f7`
- **Output:** validated against the same production schema (`direction`, `confidence` in [0, 1], `synthesis`).
- Retrieval-augmented context (RAG) is disabled, so that evidence order is the only manipulated variable.
- No capital, broker account or order is involved.

## 3. Models (two independent families)

| Model | Provider | Role |
|---|---|---|
| `deepseek-flash` | DeepSeek API | Confirmatory |
| `gemini-3.8-flash` | Google Gemini API | Confirmatory |

- **Settings:** `temperature = 0`, JSON mode, `max_tokens = 1024` (to accommodate models that consume reasoning tokens before answering).
- For every call, the identifier of the model that actually responded (`returned_model`) and, where available, the `system_fingerprint` are recorded.
- If the model version changes during data collection, data before and after the change are reported separately.
- **Declared limitation:** a third model family is not tested because of API access constraints.

## 4. Input data (synthetic)

Each **evidence set** contains 5 votes, from the regime, ml_structure, correlation, fundamental and sentiment agents. Each vote has a direction, a confidence, a quality flag and a short reason, in the production format.

**24 sets in 3 strata**

| Stratum | Vote composition | Sets |
|---|---|---|
| A — balanced conflict | 2 BUY, 2 SELL, 1 NEUTRAL, with close confidences | 8 |
| B — weak majority | 3 versus 2 | 8 |
| C — clear consensus | 4 or 5 aligned votes (control; expected: invariance) | 8 |

- Confidence values and reason texts were produced by a seeded generator and frozen before data collection (`evidence_sets.json`, seed = 20261001). SHA-256: `bd2e196a7a61e17b94f7af6ba6b161e96b889a507361f04e93500c316204f1f2`
- The data are synthetic to rule out market-information leakage (Li et al., 2025) and to keep content fully controlled.

## 5. Design

For each model and each set:

- **Permutation condition (P):** all 120 possible orders of the 5 votes, once each. The design is balanced: each vote appears exactly 24 times in each position.
- **Repeat condition (R):** the canonical order (alphabetical by `agent_type`, the order being implemented in the production system) repeated **40 times**. This condition measures the model's intrinsic noise under a fixed input.

**Volume:** 24 × (120 + 40) = **3,840 calls per model**, 7,680 in total.

**Execution order:** all calls (both models, both conditions, all sets) are randomly interleaved with a fixed seed, so that temporal drift or server-load changes cannot coincide with any condition. Data collection may span several days because of daily API quotas.

## 6. Hypotheses and pre-specified analysis

### H1 — Order sensitivity beyond noise (confirmatory, per model)

- **Per-set index:** diversity of the output direction, measured by the **unbiased Gini–Simpson index**, D = n/(n−1) × (1 − Σp̂²).
- **Statistic:** Δ = D_P − D_R per set, and the mean of Δ across the 24 sets.
- **Test:** one-sided sign-flip permutation test with 10,000 permutations.
- **Smallest effect size of interest (SESOI):** Δ = 0.05.
- **Power:** by simulation, ≈ 0.99 for Δ = 0.05 and ≈ 0.88 for Δ = 0.03.
- **Calibration:** the simulated type-I error rate is ≈ 1.5% at a nominal α of 1.25%. This is reported explicitly.

### H2 — Position effect (confirmatory, per model, strata A and B only)

- **Statistic:** for each trial, the mean list position (1–5) of the votes that agree with the output, minus the mean position of the disagreeing votes.
- **Null:** because the design is balanced, this difference is centred on zero if order has no effect.
- **Test:** two-sided permutation test (outputs permuted across trials within each set).
- **Direction:** negative = primacy (votes early in the list dominate); positive = recency.

### H3 — Decision impact (descriptive, no test)

- In each trial, the Research output, together with the 5 votes of the same set, is passed to a replica of the deterministic `AgentCoordinator.aggregate` function using the **production weights of 26 September 2026** (Research = 1.0).
- **Reported:** the share of trials whose consensus decision (direction and whether consensus is reached) differs from the decision obtained with the modal output of condition R, **separately for condition P and condition R**. The difference between the two is the share of decision changes attributable to order, net of the model's intrinsic noise.
- The same computation is repeated with the current weight (Research = 0). Structural expectation: zero.

### Exploratory (non-confirmatory) analyses

- Dispersion of confidence in condition P versus condition R
- Differences between strata (A, B, C)
- Invalid-output rate by condition

### Multiplicity and absence of effect

- **Multiple-comparison correction:** Holm's method across the 4 confirmatory tests (H1 and H2, each for 2 models). Family-wise α = 0.05.
- **Claims of "no sensitivity":** only via a TOST equivalence test with bounds |Δ| < 0.02. A non-significant result alone is never reported as invariance.

## 7. Decision criteria

| Result | Pre-registered interpretation |
|---|---|
| H1 significant **and** Δ ≥ 0.05 | The model is order-sensitive; canonical ordering (M1) and zero weight are empirically justified |
| TOST significant | Within ±0.02, no sensitivity beyond noise |
| Neither | Inconclusive; reported as such |

**All results — positive, negative or inconclusive — will be published.**

## 8. Invalid data, errors and stopping rule

- **Stopping rule:** fixed N; no interim looks at the results and no early stopping.
- **Network error or HTTP 5xx:** up to 5 retries with exponential backoff; after that, the trial is recorded and reported as missing.
- **HTTP 429 (API quota reached):** after 5 retries, collection for that model is paused and resumed from the same point in a later run. The trial is not lost, and the scheduled order is unchanged.
- **Output not matching the schema:** not retried. It is labelled INVALID, excluded from the primary analysis, and included in a sensitivity analysis as a fourth output category. If the invalid rate exceeds 5%, this is declared as a deviation from the plan.
- **Release:** the harness code, generator, seeds and raw logs of all trials (prompt, response, returned model, time) will be published on GitHub alongside the paper. API keys never appear in any log.

## 9. Pre-declared limitations

- The data are synthetic; external validity for live markets is not claimed directly.
- Only two model families are tested; results depend on the specific model versions.
- `temperature = 0` does not guarantee full determinism with these APIs; condition R is designed precisely to isolate this noise.
- No conclusion about the profitability of ZVAKTHOR is drawn or reported.

## 10. Frozen files

`run_trials.py` verifies these hashes before every run and refuses to run if any file has changed. Schedule: `schedule.jsonl`, seed = 20261002, 7,680 trials.

| File | SHA-256 |
|---|---|
| `research_prompt_snapshot.txt` | `c76f4009a870fcd6802a13498178c5fe23201fbb1c39ff33e1b09b693c4ee3f7` |
| `evidence_sets.json` | `bd2e196a7a61e17b94f7af6ba6b161e96b889a507361f04e93500c316204f1f2` |
| `schedule.jsonl` | `4ffef842ef3767af8b075a815eff3a99c2f19e9532d90f8c15533cf434af9a0a` |
| `common.py` | `e23327ec6b10554052f2036cdf8f6264c5513b0dec5599beaa03f594f559e86e` |
| `generate_sets.py` | `f3266a9a1e4cf8e9d325b182bbad92b6ed11dbe2a5b5940e1d66b290146fce74` |
| `build_schedule.py` | `8e84f348e77148a844f59611036ff76e292cd6ca7ef8caf62f4cff7042a701bc` |
| `run_trials.py` | `3f37d8e620d406cddad89bcd89d1ea1dd36375c8d6e109b8810d69d15d5e6c97` |
| `analyze.py` | `0e3afd66348d90d7339dd5cf244aa2a8f9a4ec7185798d576feac174a9761e22` |

## 11. Deviations from the plan

Any deviation will be reported, with its reason and timing, in a dedicated "Deviations from Pre-Registration" section of the paper.

---

### Key references

- Barton et al. (2026). arXiv:2609.05663
- Wadi & Ma (2026). arXiv:2608.22697
- Bito, Ren & He (2026). arXiv:2608.03091
- Liu et al. (2023). *Lost in the Middle.* arXiv:2307.03172
- Zheng, C. et al. (2024). *Large Language Models Are Not Robust Multiple Choice Selectors.* ICLR 2024
- Tang, R. et al. (2024). *Found in the Middle: Permutation Self-Consistency Improves Listwise Ranking in Large Language Models.* NAACL 2024
- Li et al. (2025). arXiv:2510.07920
- Soufi (2026b, 2026c). SSRN

---

## 12. Amendment 1 (28 September 2026), registered before any data used in the confirmatory analysis

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
