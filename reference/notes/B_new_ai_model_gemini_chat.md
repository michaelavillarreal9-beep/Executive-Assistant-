# Notes: PDF B, "Michael Villarreal - New AI Model"

- **File:** `Michael_Villarreal_-_New_AI_Model.pdf`, 18 pages. The page header reads "You are an AI Agentic Model Expert assisting a new business CEO in the set up of a complex, multi-ti…"
- **What it is:** a printed export of a Gemini chat (gemini.google.com/app/823330949d716015), dated 10/14/26 in the page header.
- **How it was read:** the file has no text layer and no embedded images (Microsoft Print to PDF, vector glyphs), and no OCR engine is installed. Each page was read visually from rendered page images, including the tables and the one diagram on p.7.
- **Source limitation:** wide code blocks are **cut off at the right margin in the print itself** (pp.2-5, 9, 11-13, 16-17). Text past the margin is not recoverable from this file and has not been guessed.
- **Citation key:** `[B p.N]`, where N is the "N/18" footer.

## Epistemic status
B is **model output (Gemini), not a specification Michael authored**. Its operational claims are Gemini's reports and have not been verified. These include "no edits made" (p.1), the sweep results (pp.14-18) and "skill is now saved" (p.18). PDF A later audits several of them [A p.1].

## Structure
1. **The user prompt** [B p.1] asks the model to review the Drive files for a "multi-tier orchestration AI agent model" across Claude Pro, Gemini Pro and Runable Pro. It should state what works, what doesn't and what is missing, revise, rerun the analysis **up to 3 times** while documenting changes, and then propose a better system. The prompt also says "do not make edits unless given approval".
2. **Inventory** of Drive files [B p.1]: Project Instructions sheet, EA Dashboard doc, an archived Inbox/Tasks sheet, and Claude Recommendations (R-001 to R-030).
3. **Iteration 1, v0 to v1.0** [B pp.1-3]: assigns roles to the three model tiers, deprecates the archived sheet, adds a pre-write state drift check, and resolves the T-011 contradiction.
4. **Iteration 2, v1.0 to v2.0** [B pp.3-4]:
   - a structured 4-line handoff (`[STATE]/[DELTA]/[BLOCKER]/[GATE]` with confidence 1-5)
   - delta-only reads with a 7/14-day archival window
   - collision-proof IDs (`T-YYYYMMDD-AREA-NN`)
   - `Depends_On` keys
5. **Iteration 3, v2.0 to v3.0** [B pp.4-6]:
   - a Rule-of-3 WIP decision cap
   - a revenue/risk priority score
   - cross-model quota failover
   - a 250-word, 4-block daily briefing
6. **Proposed new system** [B pp.6-7]: a "Unified Hub-and-Spoke Command Engine", with a single stateful hub (Runable Pro) and stateless specialist spokes (Gemini Pro as sensor/auditor, Claude Pro as the workbench with domain "cartridges").
7. **Technical spec** [B pp.7-14]:
   - topology diagram (p.7) and a responsibility/boundary table (p.8)
   - daily loops (p.8)
   - SQLite schema with tables `areas`, `tasks`, `inbox_events`, `capabilities_registry` and `approval_audit_log` (pp.8-10)
   - three SQL views (pp.10-11)
   - hub, Gemini and Claude prompts (pp.11-13), the 4-line receipt (p.13), seed data (pp.13-14) and a 4-step deployment (p.14)
8. **A sweep run** [B pp.14-18]: a Gmail triage table, a calendar audit, a Drive delta, a Rule-of-3 queue and a JSON ingestion payload.
9. **Saving the skill** [B p.18]: saved as the "workspace-sensor-sweep" skill.

## Core concepts
1. **The CEO's attention is the scarcest resource** [B p.4 §3.1]. Hence the Rule of 3 [B p.4 #1, p.5], the 250-word briefing [B p.5 §4] and collapsing the backlog into one line [B p.5].
2. **A single source of truth** [B pp.2, 6-8]: one canonical state store, and dashboards rendered from it at "zero LLM tokens" [B p.6, p.7 table].
3. **Hub and stateless spokes** [B pp.6-8]: spokes do not remember task state, because the hub holds it [B p.7 #3].
4. **Hard governance gates** [B p.1, p.5 §5, p.13 §2]:
   - Client-Facing Lock: anything seen by a client, contractor, hiring manager or the public stops for review.
   - Money Lock: pricing, retainers, invoices, contracts and paid subscriptions need Michael's approval.
   - 1-5 Confidence Gate: confidence 1-2 is research-note only, 3 needs `[UNVERIFIED: …]`, and 4-5 may be proposed normally [B p.5].
   - The schema enforces "confidence ≤ 2 cannot be APPROVED" [B p.10].
5. **Approvals only through an authenticated human UI action** [B p.6, p.8 table, p.11 §2.2]. Every mutation is written to an immutable `approval_audit_log` with `actor_identity = 'MICHAEL_UI_AUTH'` [B p.10]. Any sub-agent payload setting APPROVED is rejected [B p.11].
6. **Deterministic, machine-parseable handoffs** [B p.3 §2.2 #1, p.4 table, p.13 §3]: a 4-line receipt with fields `[TASK_ID]`, `[STATE]`, `[DELTA]`, `[BLOCKER]` and `[GATE]` plus a confidence value.
7. **Context hygiene through delta-only reads** [B p.3, p.5 §2.3]: read only open or recent rows, and auto-archive DONE rows older than 14 days [B p.4, p.11].
8. **Dual-clock escalation** [B p.1, p.5 §4.2, p.10 view 2]:
   - "Manager-Slow" fires at 7 days open and "Michael-Slow" at 3 days blocked on Michael.
   - Clocks pause while an item is waiting on an external party.
   - **3-strike rule** [B p.5, p.9]: after 3 escalations with no movement, propose scoping down or dropping instead of repeating the reminder.
9. **Dependency cascade** [B p.3, p.5 §2.5, p.11]: a blocked or waiting parent sets its children to WAITING_ON_DEPENDENCY and suppresses false escalations [B p.4 table].
10. **Failover** [B p.4 #3, p.5, p.12 §4]: if Claude hits a quota, Gemini assumes the EA role, and if Runable is offline, Gemini runs the morning check.
11. **Idempotency and deduplication** [B p.3, p.5 §2.4, p.9]: `intent_hash = SHA256(area_code || normalized_summary)` is UNIQUE, and an intent check runs before creating a row.
12. **Iterative self-review** [B p.1 prompt; the structure of pp.1-6]: each cycle runs audit, then revise, then rerun the analysis, then state what improved and what still fails, with a changelog [B p.6 table]. **This is the closest thing in either PDF to a reflection/critic loop.**

## Roles defined (candidate sub-agents)
| Role | Responsibilities | Source |
|---|---|---|
| **Hub / Orchestrator** (Runable Pro) | Canonical database, cron scheduler, deterministic dashboard UI, dual-clock escalation engine. Never changes `michaels_ok` through LLM inference. | B p.7 diagram, p.8 table, p.11 §3.1 |
| **Sensor / Auditor** (Gemini Pro) | Reads Gmail, Calendar and Drive, runs T-011 email triage and the Drive delta audit, acts as failover EA. Outputs JSON and stages Gmail *drafts* only. Never sends email or invites external guests. | B p.8 table, pp.11-12 §3.2 |
| **Workbench** (Claude Pro), the EA persona plus 5 domain cartridges | Executive synthesis and high-craft drafts. Cartridges: CON (Villarreal Consultants), CAR (career / large-loss PM), MUS (vocal and choral), POD (podcast), PER (personal logistics). Returns finished drafts plus the 4-line receipt. Never keeps state. | B p.7 #3, p.8 table, pp.12-13 §3.3 |
| **Michael (CEO)** | The only actor who can approve or decline, or set top priority. | B p.7 diagram, p.9 schema comment, p.11 |

## Key definitions
- **Areas and tier weights** [B p.5, p.8]: CON 3.0, CAR 3.0, PER 2.5, MUS 2.0, POD 1.0, ALL 1.0.
- **Task statuses** [B p.9]: NOT_STARTED, IN_PROGRESS, BLOCKED, WAITING_ON_MICHAEL, WAITING_ON_EXTERNAL, WAITING_ON_DEPENDENCY, DONE, DROPPED.
- **`michaels_ok` values** [B p.9]: NOT_NEEDED, PENDING, APPROVED, DECLINED, LATER.
- **Inbox event types** [B p.9]: STATUS_CHANGE, QUESTION, EMAIL_TRIAGE, CALENDAR_REQ, and a fourth value cut off in the print. B p.16 shows an `AUDIT_FLAG` value in use.
- **Capability types** [B p.9]: SKILL, CONNECTOR, APP_FEATURE, WORKFLOW.

## Requirements and constraints
- Do not edit Drive files without approval [B p.1 prompt].
- Never write to the archived sheet [B p.2, p.5 §2.1].
- Run a pre-flight drift check by comparing the dashboard's "Updated" date with the latest task timestamp [B p.2, p.5 §2.2].
- Spokes never send external email or invites [B p.8 table].
- Every task turn ends with the 4-line receipt [B p.13 §3].
- The briefing is at most 250 words, in exactly 4 blocks [B p.5 §4, p.11].
- The prompt caps the review at **3 iterations** [B p.1 prompt].

## Internal inconsistencies (within B itself)
- **Override rule vs score.** "Explicit directive always overrides calculated scores" [B p.5 §3 #1]. However, the view sorts `is_ceo_top_priority DESC` first [B p.11], and the sweep payload sets that flag to 1 on four model-created tasks [B pp.17-18], which contradicts "1 if explicitly named by Michael" [B p.9].
- **Approval written by the model.** The sweep payload sets `michaels_ok: "APPROVED"` on T-20261014-PER-01 [B p.18], which contradicts the hard restrictions on B p.8 and p.11.
- **Deadline window.** The prompt says "Hard deadlines within 72 hours" [B p.5 §3 #2], but the escalation view uses `+2 days` [B p.10].
- **Priority formula.** The prose formula is Domain Weight × Blocker Multiplier + Deadline Urgency [B p.4], but the SQL view has *no deadline term* and adds 0.25·days_blocked [B p.11].
- **Triage classes.** The sensor prompt uses NEEDS_MICHAEL, DRAFT_STAGED and HANDLED_NOISE [B p.12], while the sweep table also uses WAITING_EXTERNAL [B p.15].
- **Hash values.** The hash is specified as SHA256 [B p.9], but the seed data and payloads use readable placeholders such as `'hash_con_cdi_license_check'` [B p.13, p.17].
- **Confidence values.** Every sweep row reports confidence 5 [B pp.14-15], including the claim of "zero emails received" from CDI.
