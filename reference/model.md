# The Model: Synthesis of the Source PDFs

**Status:** Phase 0 approved. Your answers to the open questions are recorded in §7. Architecture: `reference/architecture.md`.

**Sources** (per-PDF notes are in `reference/notes/`):
- **[A]** *Agent Stack: Email Triage and Priority Scoring Design*, 8 pp., Oct 14 2026
- **[B]** *Michael Villarreal – New AI Model*, 18 pp., a printed Gemini chat export dated 10/14/26

Citations take the form `[A p.N]` / `[B p.N]`. Anything without a citation is either my own design choice (labelled **DESIGN**) or an open question (labelled **GAP**).

---

## 0. The most important finding: what the PDFs are (and are not) about

Neither PDF uses the words "synthetic intelligence". Neither describes a general-purpose reasoning agent with episodic memory and self-written skills. **Both describe one concrete system: an AI Executive Assistant for a solo founder/CEO (Michael).** That system coordinates five life and business areas, protects the CEO's attention, and puts hard human gates on money, client-facing work and decisions [B p.1, p.4 §3.1; A p.1].

The two documents are related. **[A] is a later review of [B].** A says it critiques "two shared Gemini chats", the second being "the first plus one more turn, where the sweep protocol is saved as a Gemini skill" [A p.1]. That is exactly how B ends [B p.18]. So:
- B supplies the **architecture**: a hub with stateless spokes, roles, a schema, loops and gates.
- A supplies **corrections and the measurement and learning discipline**: code-owned fields, validators, golden sets, metrics, calibration, versioned weights, replay and rollback.

**This changes your capability list.** The PDFs define *what this intelligence is for and how it must be constrained*. They say little about generic plan/reflect/self-improve machinery. Section 4 maps each of your 8 capabilities onto what the PDFs do say, and Section 6 lists where I would be filling silence myself.

---

## 1. Shared concepts (both sources agree)

| # | Concept | A | B |
|---|---|---|---|
| C1 | **The principal's attention is the scarce resource.** Surface at most 3 decisions at a time (the "Rule of 3"). | p.7 "At most 3 items are shown" | p.4 §3.1, p.5 "Rule of 3" |
| C2 | **Hard gates** on MONEY, CLIENT_FACING and DECISION force human involvement. | p.2 | p.1, p.5 §5, p.13 §2 |
| C3 | **Only the human approves.** Only an authenticated UI action counts, never a model's say-so. | p.1, p.7 (E only from `MICHAEL_UI`) | p.6, p.8, p.10 (`MICHAEL_UI_AUTH`), p.11 |
| C4 | **One canonical state store.** Views are rendered from data rather than written by an LLM. | p.8 ("move IDs, timestamps and hashes into Runable code") | pp.6-8 |
| C5 | **Five areas with the same weights:** CON 3.0, CAR 3.0, PER 2.5, MUS 2.0, POD 1.0. | p.7 | p.5, p.8 |
| C6 | **Structured, machine-checkable outputs** instead of prose between components. | p.4 schema validator | p.3 §2.2, p.13 §3 |
| C7 | **Confidence 1-5 attached to claims**, with low confidence restricted. | p.3 | p.5 §5, p.10 |
| C8 | **Dedupe and split by intent** (`intent_hash`). | p.1 (one row per intent), p.4 | p.3, p.5 §2.4, p.9 |
| C9 | **Dependencies matter.** Blocked items should not compete for attention. | p.6 eligibility, defect #6 | p.3, p.5 §2.5, p.11 |
| C10 | **Iterate, and state what improved with evidence.** | p.8 replay, metrics | p.1 prompt; the structure of pp.1-6 |
| C11 | **Draft only, never send.** | p.2 (CLIENT_FACING + DRAFT_STAGED never sends) | p.8 table, p.12 |

## 2. Conflicts and how I resolve them

**Resolution principle:** where A and B conflict, **A wins**. A is the later document, written as an explicit review of B [A p.1], and it carries Michael's byline [A p.1]. B is unverified model output. Where A is silent, B stands.

| # | Conflict | B says | A says | **Decision** |
|---|---|---|---|---|
| X1 | Triage classes | 3 classes: NEEDS_MICHAEL, DRAFT_STAGED, HANDLED_NOISE [B p.12]. The sweep labels a LinkedIn receipt as noise [B p.15]. | 5 classes [A p.1-2]. The LinkedIn receipt is FYI_LOG, "Not noise" [A p.5 case 7]. | **Use A's 5 classes.** |
| X2 | Gate encoding | A comma-separated string with an `NO` value [B p.9] | A set, where empty replaces NO, plus a DEADLINE_72H gate derived by code [A p.2] | **A: a set, with DEADLINE_72H computed by code.** |
| X3 | Priority formula | `Domain×Blocker+Urgency` [B p.4]. The SQL version has no deadline term and an uncapped `0.25·days_blocked` [B p.11]. | `W·G·B + U + min(0.15·age,1.5) + E` [A p.6-7], with 8 named defects in B [A p.6] | **A's formula, eligibility rule and tie-break.** I verified A's worked example; all 10 numbers reproduce [A p.7]. |
| X4 | Explicit priority | "Always overrides" [B p.5]. The flag is sorted first [B p.11] and set by the model [B pp.17-18]. | An additive +4 only when `priority_source='MICHAEL_UI'`. A spoke-set flag is ignored and logged [A p.7]. | **A: additive and human-only.** |
| X5 | Who writes IDs, timestamps and hashes | The model writes them, and they are placeholders [B pp.12, 13, 17] | Code writes them, and the model cannot [A p.4, p.8] | **A: code only.** |
| X6 | Confidence | Self-reported. All sweep rows are 5 [B p.15]. | Derived from rule/model agreement. Missing-evidence claims are capped at 3. A sweep where >80% share one value is "uncalibrated" [A p.3]. | **A: derived confidence.** B's gate thresholds (1-2 note only, 3 marked UNVERIFIED) [B p.5] are applied on top of it. |
| X7 | Deadline window | "72 hours" [B p.5] vs `+2 days` [B p.10] | 72h gate; urgency bands at 24h, 72h and 7d [A p.2, p.7] | **A.** |
| X8 | Approval written in a payload | The sweep payload sets APPROVED [B p.18] | Wrong; only a UI click may [A p.1] | **A.** The validator rejects any agent-written approval. |

## 3. The model, stated as principles

Every principle below traces to a page. These are the things the architecture must satisfy.

- **P1. Purpose.** The system is an executive-assistant intelligence. Its job is to turn incoming signals into a small, correctly ranked set of decisions and drafts for one principal, while protecting that person's attention [B p.4 §3.1; A p.6].
- **P2. Hub and stateless specialists.**
  - One stateful hub owns all state, scheduling and rendering [B pp.6-8].
  - Specialists are stateless. They receive a context packet and return an artifact plus a structured receipt [B p.7 #3, p.8, p.13 §3].
- **P3. Code owns consequential fields.** IDs, timestamps, hashes, deadline flags, eligibility, scores and approval state are computed or enforced by code [A p.1, p.4, p.8].
  - The model may propose content: summaries, draftability, extra gates [A p.2].
- **P4. Validate after every model step.**
  - Schema check plus count reconciliation [A p.4].
  - Gates can only be added, never removed [A p.2].
  - Gated items are never discarded [A p.1-2].
- **P5. Human authority is exclusive.**
  - Approve, decline and explicit priority come only from an authenticated human action, and are written to an immutable audit log [B p.10-11; A p.1, p.7].
  - Nothing is ever sent externally; output is drafts only [B p.8; A p.2].
- **P6. Attention budget.**
  - At most 3 decisions, each with a recommendation [B p.5].
  - Close calls (gap < 0.5) are flagged [A p.7].
  - The briefing is ≤ 250 words in 4 blocks [B p.5].
- **P7. Epistemic honesty.**
  - Confidence is derived, not self-declared [A p.3].
  - Absence claims state the query, window and source, and are capped at 3 [A p.3].
  - Confidence ≤ 2 cannot be proposed for approval, and 3 must carry `[UNVERIFIED: …]` [B p.5, p.10].
- **P8. Context hygiene.**
  - Read deltas only: open or recent items [B p.3, p.5 §2.3].
  - Run a drift check before writing [B p.2, p.5 §2.2].
- **P9. Escalation without nagging.**
  - Dual clocks: 7 days for "Manager-Slow" and 3 days for "Michael-Slow". Clocks pause while waiting on an external party.
  - The 3-strike rule leads to a scope-down or drop proposal [B p.5, p.10].
- **P10. Improvement must be measured, bounded and reversible.**
  - Learn from the principal's revealed choices [A p.6, p.8].
  - Evaluate against a golden set with fixed metrics [A p.2-5, p.8].
  - Replay every change before shipping, cap change per cycle, version every config, and roll back automatically on defined triggers [A p.8].
  - Shadow first, then promote on threshold [A p.4].
  - A bounded number of review iterations, each documenting what improved and what still fails [B p.1 prompt, p.6 changelog].
- **P11. Privacy by minimization.** Store only redacted snippets, masked numbers and amount buckets, and keep references only for legal or financial content [A p.3].

## 4. Your 8 capabilities, adapted to the model

| Your capability | What the PDFs say | Adaptation (and what changed) |
|---|---|---|
| 1. Perception & context | The Sensor role ingests Gmail, Calendar and Drive and emits a structured JSON digest [B p.8, p.12]. Features are split between code and LLM [A p.2]. | Perception = **Sensor** module. It turns raw inputs into typed records with code-computed features. *Changed:* inputs are structured events (messages, calendar items, tasks), not just "files and notes". |
| 2. Memory | Working state is the hub's task and inbox tables [B pp.8-9]. History comes from logged renders, labels, `approval_audit_log` and versioned configs [A p.8; B p.10]. | Working memory = the hub state store. **Episodic** (`/memory/episodes/`) = one record per run: inputs, decisions, metrics, lessons. **Semantic** (`/memory/knowledge/`) = distilled facts such as the contact registry [A p.2] and area weights. *The PDFs do not specify an episodic/semantic split; that is* **DESIGN** *(see G6).* |
| 3. Planning | Decompose by intent, one row per ask [A p.1]. Dependencies via `depends_on` [B p.9]. Each task row has a status, gates, due date and blocker. | The plan is a set of task rows. Each step carries success criteria, `depends_on`, gates and a risk note (risk = its gates plus confidence). Plans are revised when the dependency cascade fires [B p.11]. *The PDFs do not describe multi-step goal decomposition beyond this* (G7). |
| 4. Action | Spokes act only through narrow, permitted channels: read, draft, return a receipt [B p.8]. Writes go only to the hub [B p.8]. | A single dispatch layer with an allow-list per role. Every call is logged. Send, delete, spend and approve are **blocked in code**, not just discouraged. |
| 5. Reflection / critic | Validators [A p.2, p.4]. Error costs [A p.3]. Metrics with targets [A p.2, p.8]. B's "what works / what doesn't / what's missing" review cycle [B p.1-6]. | The critic is two layers. (a) **A deterministic validator and scorer**, which uses A's metrics and error costs against the golden set and logged choices. (b) **A short model-written review** in B's format (works / doesn't / missing, plus one concrete improvement). The numbers come from (a), never from (b). |
| 6. Self-improvement | Weight learning: before 30 pairs, a simple rule adds +0.25 to an area's weight after more than 3 pulls; after that, a Bradley-Terry fit. Changes are capped at 20% per week, replayed before shipping, versioned, and rolled back automatically [A p.8]. A capability registry with confidence gates [B p.9-10]. Saving a protocol as a reusable skill [B p.18]. | `/skills/` holds reusable procedures, and `/config/scoring_config_vN` holds learnable weights. **Every change is proposed, replayed against history, compared before and after, and only then adopted**; this is P10. Gates, approval rules and validator rules are **never** auto-modified. |
| 7. Specialist sub-agents | Hub/Orchestrator, Sensor/Auditor, Workbench with 5 cartridges, and the human principal [B pp.7-8, 12-13] | `/agents/`: `orchestrator`, `sensor` (triage and calendar), `workbench-{con,car,mus,pod,per}`, and `critic` (an addition; see G5). Handoffs use B's 4-line receipt [B p.13]. *Model vendors (Gemini/Claude/Runable) are dropped as role names, since roles are what matter* (G1). |
| 8. Metacognition | Confidence gate [B p.5]. Derived confidence and calibration checks [A p.3]. `[UNVERIFIED: …]` tagging [B p.5]. | Before acting, the agent states its derived confidence and its known unknowns. Low confidence on a gated item means it **asks you** rather than guessing (P5, P7). |

## 5. Design decisions so far (each traceable)

- **D1.** Implement A's triage classifier contract: 5 classes, a gate set, and validator rules. A's 12-case golden set (14 rows) is the first acceptance test [A p.1-6].
- **D2.** Implement A's priority scorer, with its eligibility rule, tie-break, Rule of 3 and close-call flag. A's p.7 worked example is a unit test, with expected outputs 9.25 / 6.35 / 6.2 / 6.0 / not eligible [A p.6-7].
- **D3.** Use B's state model (tasks, inbox events, capabilities, approval audit log) and its statuses, with A's corrections applied [B pp.8-10; A p.6].
- **D4.** Approvals are recorded only through a separate human-run command, never through agent output [A p.1; B p.11]. The mechanism is G3.
- **D5.** Self-improvement follows A's loop [A p.8]: log choices, form pairs, apply the rule (or Bradley-Terry after 30 pairs), cap the change, replay, version, and roll back on triggers.
- **D6.** Use plain files (JSON/JSONL/Markdown) plus small Python scripts with the standard library, and SQLite only if needed. B proposes SQLite [B p.8]; your brief prefers plain files. *Leaning:* JSONL for logs and episodes, SQLite for the state store so B's views can be ported almost as written. Decided in Phase 1.

## 6. Gaps, ambiguities and questions for you

**G1. What is this repo, relative to the PDFs' stack?** The PDFs place the hub in Runable Pro and the spokes in Gemini and Claude [B p.7]. Options:
- (a) This repo is a local, working **reference implementation of the hub**, with the spokes simulated by role prompts.
- (b) A harness for designing and testing logic that you'll later port to Runable.
- (c) Something else.

*My recommendation:* (a) and (b) together. It is a self-contained, testable implementation of the model.

**G2. Real data or fixtures?** A says the golden set lives only in Runable and "nothing is pasted into Claude" [A p.3]. This session has Gmail, Calendar and Drive connectors, but using them would conflict with A p.3.

*Recommendation:* use **synthetic and redacted fixtures** derived from A's 12 cases. Touch no real mailbox unless you explicitly approve read-only access.

**G3. What counts as the "UI click"?** Your approval must be unforgeable by the agent [A p.1; B p.11].

*Proposal:* a separate script you run yourself, `./approve <id>`, which writes the audit log with `actor=HUMAN_CLI`. The agent's dispatch layer is forbidden from calling it. Is that acceptable?

**G4. Who plays the model?** Spokes need LLM judgment for summaries, draftability and drafts.
- (a) **Me (Claude Code) in-session**, with scripts handling everything deterministic. This needs no API key and incurs no spend.
- (b) Anthropic API calls from the scripts. This needs a key and **costs money**, so it requires your approval.

*Recommendation:* (a), with the model calls behind one interface so (b) can be swapped in later.

**G5. Critic, episodic memory and skills are not in the PDFs as such.** I've mapped them onto A's evaluation loop and B's review cycle (§4). Please confirm you want them added on that basis.

**G6. Memory split.** The episodic/semantic distinction comes from your brief, not the PDFs. I'm keeping it, and grounding the semantic contents in A's contact registry and the area weights.

**G7. Goal decomposition depth.** The PDFs decompose work into intents and tasks with dependencies, nothing deeper. I'll keep planning at that granularity unless you want more.

**G8. Phase 4 demo goal is unspecified** (your brief says "[INSERT A SAMPLE GOAL HERE]").

*Proposal, fully grounded in A:* "Triage this week's (synthetic) inbox and produce the Rule-of-3 briefing."
- Run 1 is scored on A's metrics.
- Simulated "Michael first-action" picks then feed the learning loop.
- Run 2 is re-scored, and the before/after comparison is shown.

Does that work, or do you have a real goal in mind?

**G9. Undefined terms in A:**
- "Every upstream dependency is DONE or *owned by Michael*" [A p.6]. My proposal: `assigned_to = MICHAEL`.
- How date-only deadlines become `hours_to_deadline`. My proposal: end of day, America/Los_Angeles, inferred from the −07:00 offsets on [B p.12, p.16]. **Uncertain.**

**G10. Two `intent_hash` definitions:**
- Email intent: `sha256(thread_id|last_msg_id|intent_idx)` [A p.4].
- Task: `SHA256(area||normalized_summary)` [B p.9].

*Proposal:* keep both, scoped (`email_intent_hash` and `task_intent_hash`).

**G11. Escalation clocks** [B p.5, p.10] are not covered by A. I'll keep them as specified in B unless you object. B also mixes calendar days with "business days" (`'7-10 business days'` [B p.13]); I'll use calendar days.

**G12. Truncated source text.** B's prompt code blocks are cut off at the page margin [B pp.2-5, 11-13, 16-17]. I won't reconstruct the missing text. If the full prompts matter, please share them (for example, the Drive files).

**G13. Privacy of this repo.** The notes mention case names already present in A (e.g. "Fox Plaza rent NSF"). If the GitHub repo is or may become public, I'll replace them with neutral IDs. Is it private?

**G14. Model metric thresholds** are "starting values to calibrate" [A p.1]. I'll use them as-is for pass/fail.

---

## 7. Your decisions (2026-10-14)

These override the PDFs wherever they differ. Each override is listed so it stays traceable.

| # | Question | Your answer | Effect on the model |
|---|---|---|---|
| R1 (G1) | Where does it run? | **Inside Runable.** | Runable is the hub: the state database, the screens and your buttons [B pp.6-8]. This repo holds the logic, rules, tests, prompts, memory and the Runable build spec. |
| R2 (G2) | Real or test email? | **Read-only real email.** | **Overrides A p.3** ("nothing is pasted into Claude"), with your approval. A's storage limits still apply to everything saved [A p.3]. Nothing is sent, drafted in Gmail, labelled, moved or deleted. |
| R3 (G3) | How do you approve? | **Simple commands you run yourself.** | Approve, Decline, Done and Reopen are buttons or commands in Runable that only you can press [B p.11; A p.1]. I have no Runable login, so I cannot fake them. |
| R4 (G4) | Who does the thinking? | **Claude, in-session.** | Claude replaces Gemini as the Sensor role [B p.8]. No API spend. |
| R5 (G8) | Demo goal | **Run email → all pending items (no limit) → track what's completed each week.** | **Overrides the Rule of 3** [A p.7; B p.5] for the pending list: every pending item is shown, ranked by A's score. Adds a weekly completed report, built on B's Sunday routine and `date_closed` [B p.9, p.11]. |
| R6 (G13) | Repo privacy | **Private, but keep it neutral.** | Committed files use area codes, IDs and neutral descriptions, with no personal names. Detailed text lives in Runable only. |

| R7 | Runable import/export | **Yes, it can import a file and export a CSV.** | The file route is used. No Runable API is assumed. |
| R8 | Top-3 marker | **No.** | The full pending list is ranked with no top-3 marker. |
| R9 | Run cadence | **Do one same day, then every 7 days.** | Run 1 covers today's email. Later runs are every 7 days. |
| R10 | Correction time | **Yes, about 10 minutes.** | Your Run 1 corrections are the labels for Run 2's comparison. |

**Still open** (my defaults are noted; please object if needed):
- **G9:** I'm treating "owned by Michael" as `assigned_to = MICHAEL`. Deadlines with no time are treated as end of day, America/Los_Angeles. **Uncertain.**
- **G10:** I'm keeping both hash types, scoped separately.
- **G11:** I'm keeping B's escalation clocks, counted in calendar days.
- **G12:** I'm not reconstructing B's truncated prompt text.
- **G14:** I'm using A's thresholds as written.
