# Notes: PDF A, "Agent Stack: Email Triage and Priority Scoring Design"

- **File:** `Agent_Stack_Email_Triage_and_Priority_Scoring_Design.pdf`, 8 pages, dated Oct 14, 2026, author @Michael Villarreal (p.1)
- **How it was read:** text layer via `pdftotext -layout`, one page at a time. Every page is text and tables. There are no figures, and no OCR was needed.
- **Citation key:** `[A p.N]`

## What it is
This is a design review of an existing three-model stack (Claude Pro, Gemini Pro, Runable Pro). It critiques "two shared Gemini chats" [A p.1], and the second of those chats is PDF B (see the cross-reference in model.md). Its thesis is that **the biggest risks are model-written fields that should come from code**, so it puts code in charge of those fields [A p.1].

## Core concepts
1. **Code over model for consequential fields.** IDs, timestamps, hashes, deadline flags and approval state are computed or enforced by code, and the model cannot write them [A p.1, p.4, p.8 "Where to start" #1].
2. **Validator after the model.** The model's output passes through rules it cannot override. Rules may only *add* gates, never remove them [A p.2].
3. **Explicit error costs.** Errors are weighted asymmetrically: a gated item sent to noise costs 20, a gated item misclassified otherwise costs 10, a false NEEDS_MICHAEL costs 1, and an FYI_LOG/NOISE swap costs 0.2 [A p.3].
4. **Measured improvement, not asserted improvement.** The design includes a golden set, a time-based split grouped by thread, a weekly confusion matrix, target metrics, shadow mode, canary rollout and promotion thresholds [A p.3-4].
5. **Calibration.** Confidence is *derived* rather than self-reported. Rules and model agreeing with quoted evidence gives 5, and disagreement caps confidence at 3. Claims from missing evidence must state the query, window and mailbox, are capped at 3, and need a `follow_up_on` date. If more than 80% of a sweep shares one confidence value, the payload is marked uncalibrated [A p.3].
6. **Learning from the principal's revealed preferences.** The label is Michael's *first action* from each Rule-of-3 render [A p.6]. Renders become pairwise preferences fed to a Bradley-Terry fit with a prior on the current weights. Changes are capped at 20% per week and need at least 30 new pairs. Before that, a simple rule applies: an area pulled out of the top 3 more than 3 times gets +0.25 [A p.8].
7. **Versioning and rollback.** Weights are stored as `scoring_config_vN`, and every render logs the version. Every weight change is replayed against logged history before it ships, and an automatic rollback fires on defined triggers [A p.8].
8. **Privacy by minimization.** Store at most a 200-character redacted snippet, mask account, routing, policy, license and SSN numbers, bucket amounts, and store only a reference for legal and financial threads. The golden set stays in Runable only, and "nothing is pasted into Claude" [A p.3].

## Framework / model proposed
**Task 1, email triage classifier (T-011)** [A p.1-6]
- One row per *intent*, so multi-ask threads are split (cases 5a/5b and 6a/6b) [A p.1, p.5].
- There are exactly 5 classes: `NEEDS_MICHAEL`, `DRAFT_STAGED`, `WAITING_EXTERNAL`, `FYI_LOG`, `NOISE` [A p.1-2].
- Gates form a set drawn from `MONEY`, `CLIENT_FACING`, `DECISION` and `DEADLINE_72H`. An empty set replaces "NO" [A p.2].
- Validator rules [A p.2]:
  - MONEY or CLIENT_FACING means the class cannot be NOISE.
  - MONEY alone means the class must be at least FYI_LOG.
  - DEADLINE_72H is derived by code from the extracted date.
  - CLIENT_FACING with DRAFT_STAGED never sends.
- Features [A p.2]:
  - Computed by code: sender domain mapped to the contact registry, last sender, unanswered count, days since last inbound, `internalDate`, regex-detected amounts, extracted dates, attachment type, Gmail category.
  - Supplied by the LLM: requested action, draftability, summary, extra gates.
- Target metrics [A p.2]: recall on gated items ≥ 0.98, gated items sent to noise = 0, per-gate recall ≥ 0.95, NEEDS_MICHAEL precision ≥ 0.70.
- Serving [A p.4]: a validator rejects the payload on schema failure or a count/rows mismatch, sets the timestamp from `internalDate`, and computes `intent_hash = sha256(thread_id|last_msg_id|intent_idx)`.
- Drift monitors [A p.4]: six of them, with stated thresholds.
- Seed golden set [A p.4-6]: 12 cases (7 observed, 5 invented). Cases 5 and 6 are split into a/b, giving 14 rows.

**Task 2, priority scoring** [A p.6-8]
- Eligibility [A p.6]: `michaels_ok = PENDING`, status is not WAITING_ON_EXTERNAL or DONE, and every upstream dependency is DONE or owned by Michael. Ineligible items go to a "Waiting" panel.
- Score formula [A p.6-7]: `score = W_area·G·B + U(hours_to_deadline) + min(0.15·age_days, 1.5) + E`, where:
  - W_area: CON 3.0, CAR 3.0, PER 2.5, MUS 2.0, POD 1.0.
  - G uses the highest gate only: MONEY 1.3, CLIENT_FACING 1.2, DECISION 1.1, otherwise 1.0.
  - B is 1.5 if the item is blocked on Michael, otherwise 1.0.
  - U is 7 if overdue, 6 if due within 24h, 4 within 72h, 2 within 7 days, otherwise 0.
  - E is +4 only when `priority_source='MICHAEL_UI'`. A flag set by a spoke is ignored and logged.
- Ranking rules [A p.7]: ties break by earlier deadline, then `task_id`. At most 3 items are shown. A gap under 0.5 between two items is reported as a "close call".
- Evaluation targets [A p.8]: top-3 hit rate ≥ 2/3 averaged over 2 weeks, NDCG@5 ≥ 0.8, Kendall tau ≥ 0.5, and regret = 0. A regret is a MONEY or CLIENT_FACING item due within 24h that is eligible but falls outside the top 3, and each one is an incident.
- Rollback triggers [A p.8]: one regret, a top-3 hit rate below 1.5/3, or a non-Michael explicit boost. Separately, more than 3 items in the 24h band raises a "backlog needs triage" alert.

## Key definitions
- **Gate:** a consequence tag that forces human involvement [A p.2].
- **Gated item:** an item with a non-empty gate set [A p.2-3].
- **Regret:** defined under the evaluation targets above [A p.8].
- **Close call:** a score gap below 0.5 [A p.7].
- **Shadow mode:** the new output is written to `triage_shadow` while only the old output is shown [A p.4].

## Defects it identifies in B
- The saved skill has placeholder `timestamp` and `intent_hash` values [A p.1].
- Gemini can set APPROVED "on your say-so in chat", while only a UI click should be able to [A p.1].
- Gemini self-assigned `is_ceo_top_priority = 1` on four tasks [A p.1, p.6 #2].
- The SQL priority view has 8 defects [A p.6]: no deadline term, the override flag, PENDING-external items entering the view, an uncapped age term, gates carrying no weight, dependencies ignored, the prompt and SQL disagreeing, and no tie-break or versioning.
- There is an 11-to-12 count drift between the reported count and rows written [A p.4].

## Requirements and constraints
- Gated items must never land in noise, and code enforces this [A p.1].
- No model writes IDs, timestamps or hashes [A p.8].
- Only Michael, through a UI action, can approve or set explicit priority [A p.1, p.7].
- Every weight change is replayed before it ships, capped at 20% per week, versioned and rollback-able [A p.8].
- Privacy limits apply to what gets stored [A p.3].
- **The document itself says these metric thresholds are "starting values to calibrate"** [A p.1].

## Ambiguities noticed
- "Owned by Michael" in the eligibility rule is not defined [A p.6].
- There are two notions of `intent_hash`. A's email-level hash is `thread|msg|idx` [A p.4], while B has a task-level hash. Whether they replace each other or coexist is unstated.
- How `hours_to_deadline` is computed for date-only deadlines (which timezone, what time of day) is not specified.
- How "blocked on Michael" (B) relates to `michaels_ok = PENDING` is not specified.
