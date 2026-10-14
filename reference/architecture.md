# Architecture (Phase 1 proposal)

**Status:** **awaiting your approval.** Your answers to the four questions are recorded in §12. No code has been written yet.

**How to read the citations:** each section traces back to `reference/model.md`:
- `P#` points to a principle in §3
- `R#` points to one of your decisions in §7
- `[A p.N]` / `[B p.N]` points to a page in the PDFs

---

## 1. The big picture

```
           YOU
            │  buttons in Runable: Approve · Decline · Done · Reopen · Reclassify · Dismiss
            ▼
 ┌──────────────────────────────────────────────┐
 │ RUNABLE APP  (the hub: holds the truth)      │   B pp.6-8, R1
 │  • database of items, decisions, audit log   │
 │  • screens: Pending (all, ranked) · Waiting  │
 │             · Completed this week            │
 │  • only you can approve or close things      │   P5, R3
 └───────────▲───────────────────────┬──────────┘
   new items │                       │ export of state + your corrections
   (JSON)    │                       ▼
 ┌───────────┴──────────────────────────────────┐
 │ CLAUDE SESSION  (the sensor + checker)        │   B p.8 Sensor role, R4
 │  reads Gmail (READ-ONLY) → splits into asks   │   R2
 │  → code computes IDs, dates, gates, scores    │   P3, A p.4
 │  → validator → ranked pending list            │   P4, A p.2
 │  → critic grades the run → memory + lessons   │   P10, A p.8
 └───────────┬──────────────────────────────────┘
             │ reads and writes
             ▼
 THIS REPO: rules, code, tests, prompts, memory, skills, logs
```

**In one sentence:** Runable is where you *see and decide*, Claude is what *reads and sorts*, and this repo is the *brain's notebook*. The notebook holds the rules, what was learned and a log of everything done.

## 2. Who does what

| Part | Does | Never does |
|---|---|---|
| **You** | Approve or decline, mark done, correct mistakes | (nothing is restricted for you) |
| **Runable app** | Stores every item, shows the screens, records your clicks in an audit log [B p.10] | Lets any AI set "Approved" [B p.11] |
| **Claude (me)** | Reads email, splits threads into separate asks, classifies them, drafts *text* replies for your review, ranks items, runs the critic, writes memory | Sends, replies, forwards, drafts in Gmail, labels, archives or deletes mail; approves anything; spends money |
| **Python code in the repo** | IDs, timestamps, hashes, deadline flags, gate rules, scores, privacy redaction, metrics | Uses the network or makes judgment calls |

## 3. The three loops

### Loop 1: "Run email" (you say it, or later on a schedule)
1. **Remember.** Read `memory/knowledge/INDEX.md`, the last 3 episodes and the relevant skills. State my confidence and what I don't know (capability 8).
2. **Catch up.** Load the latest Runable export, so I know what you finished, approved or corrected since the last run.
3. **Read email (read-only).** The first run covers today's email only. After that, a run every 7 days covers the 7 days since the last run (§12).
4. **Split and classify.** One row per ask [A p.1]. Code computes the features [A p.2]. I add the summary, the requested action and any extra gates.
5. **Validate.** Code enforces the gate rules: money or client items can never be junk, and a deadline within 72h becomes a computed gate [A p.2]. Confidence is derived from the evidence, not self-reported [A p.3]. Anything failing validation is set aside and reported, never silently dropped.
6. **Dedupe** against items that already exist, using the intent hash [A p.4; B p.9].
7. **Spot finished work.** If an email shows something is resolved (you replied, a receipt arrived, the other party confirmed), the item is marked **"Looks done? (evidence: …)"**. Only you close it.
8. **Rank everything pending.** Use A's score [A p.6-7], with **no top-3 limit** and no top-3 marker (R5, §12). Waiting-on-others items go in their own list with a follow-up date [A p.6]. Near-ties are flagged [A p.7].
9. **Hand off** a JSON file for Runable, plus a readable pending list in chat.
10. **Critic pass.** Grade the run on A's metrics against your past corrections. Write one episode and one lesson. Propose at most one improvement, which is tested before it is used (§6).

### Loop 2: You, in Runable (any time)
Your buttons: **Approve, Decline, Done, Reopen, Reclassify, Dismiss ("not mine"), Add item.**
- Every click is logged with you as the actor [B p.10].
- **Your corrections are the system's teacher.** Each Reclassify, Dismiss or Add counts as a label [A p.3, p.6].

### Loop 3: "Weekly review" (Sunday, per B p.11)
- **Completed this week**, by area, with counts and the dates each item was closed.
- **Still open**, with age and anything that slipped past its deadline.
- **Comparison with last week:** items closed, items opened, net change.
- **System scorecard:** how accurate the sorting was this week, measured against your corrections.
- Items closed more than 14 days ago are archived [B p.11].

## 4. Folder layout

```
reference/          PDFs → notes, model.md, architecture.md (this file)
agents/             one prompt file per role (§7)
core/               small Python modules (stdlib only, no frameworks)
  ids.py              IDs, intent hashes, timestamps          [A p.4]
  redact.py           masking, 200-char snippets, amount buckets [A p.3]
  gates.py            validator rules                          [A p.2]
  confidence.py       derived confidence + calibration checks  [A p.3]
  scoring.py          eligibility + score + tie-break          [A p.6-7]
  metrics.py          recall, precision, confusion matrix      [A p.2-3]
  weekly.py           completed/open report                    [B p.11]
  memory.py           read/write episodes + knowledge
  dispatch.py         one entry point for every script action, logged
bin/                commands: run-email, import-runable, weekly, eval
config/             scoring_config_v1.json (versioned weights) [A p.8]
memory/
  working/          current_run.json (scratch, reset each run)
  episodes/         2026-10-14-run-01.md …  (one per run)
  knowledge/        INDEX.md, contacts.json, rules.json, preferences.md
skills/             reusable procedures (triage-email.md, weekly-review.md, …)
runable/            BUILD_SPEC.md (paste into Runable), schema.sql, payload.schema.json
exchange/           to_runable/ and from_runable/ files (gitignored: real data)
tests/              golden cases (neutral wording) + unit tests
logs/               actions.log (why) + tool-calls.log (what), plain text
.claude/settings.json   hard blocks on email/calendar/drive writes + logging hook
```

**Privacy (R6, A p.3):** files containing real email data (`exchange/`, `memory/working/`) are **gitignored**. Committed memory uses IDs, area codes and neutral wording only.

## 5. Data formats (plain JSON / Markdown)

**Item**: one per ask. These are B's task fields with A's fixes applied:
```json
{ "item_id": "T-20261014-CON-01", "email_intent_hash": "sha256…", "area": "CON",
  "class": "NEEDS_MICHAEL", "gates": ["MONEY","CLIENT_FACING"], "status": "NOT_STARTED",
  "summary": "Neutral one-line summary", "due": "2026-10-16", "follow_up_on": null,
  "depends_on": null, "confidence": 4, "evidence": "quoted ≤200 chars, redacted",
  "score": 6.2, "close_call": false, "looks_done": null, "source": "gmail:<message_id>" }
```

**Handoff receipt** from any role, 4 lines [B p.13]:
```
[TASK_ID]: …   [STATE]: …   [DELTA]: …   [BLOCKER]: …   [GATE]: … (Confidence: n)
```

**Episode** (`memory/episodes/*.md`): the goal, inputs (counts only), actions, results, the metrics table, what went wrong, the lesson, and the proposed improvement.

**Knowledge** (`memory/knowledge/`):
- `contacts.json`: sender domain → area, plus a flag for known noise
- `rules.json`: keyword and gate rules
- `preferences.md`: your stated preferences
- `INDEX.md`: a one-line entry for each file

**Skill** (`skills/*.md`): when to use it, steps, checks, a version number, and the evidence that justified it.

**Logs**: one line per action in the form `timestamp | phase | action | reason`.

## 6. How it gets better (and how we prove it)

What it learns from: **your corrections in Runable** [A p.3, p.6]. A Reclassify means it sorted something wrong. A Dismiss means it raised something that wasn't yours. An Add means it missed something.

What it is allowed to change:
- the contact and area map
- the noise list and keyword rules
- the skill instructions
- the score weights, capped at ±20% per week [A p.8]

What it can **never** change: the gate rules, the read-only block, approval rules, or privacy rules (P5, guardrails).

The **safe-change routine** [A p.8]:
1. The critic proposes one change.
2. The change is replayed on every labelled item from the past.
3. It is adopted only if (a) money or client items sent to junk stays at **0**, and (b) no metric gets worse.
4. The change is saved as a new version, with the before/after numbers in the episode.
5. It rolls back automatically if a later run gets worse.

**Demo proof (Phases 4-5):**
1. Run 1 on today's email.
2. You spend about 10 minutes correcting it in Runable.
3. The critic learns from your corrections.
4. Run 2 on the same day's email.
5. A before/after table on A's metrics, taken from the logs and memory files.

## 7. Roles (`agents/`)

| File | Role | From |
|---|---|---|
| `orchestrator.md` | Runs the loops, routes work, enforces the 3-failures-then-ask rule | B p.7-8 hub role |
| `sensor.md` | Reads email, splits it into asks, classifies them, spots finished work | B p.8, p.12 (Gemini's job, now mine, R4) |
| `critic.md` | Grades runs, writes lessons, proposes one improvement | A p.2-4, p.8; B p.1-6 review cycle |
| `workbench-con/car/mus/pod/per.md` | Area specialists that draft text replies and documents for your review | B p.12-13 cartridges |

**Handoffs:** the orchestrator sends a role a short brief; the role returns the 4-line receipt.

## 8. Safety, enforced by settings rather than promises

- **`.claude/settings.json` deny list** blocks every Gmail write tool: send, reply, forward, drafts, labels, trash and spam. Calendar and Drive write tools are blocked too. This is enforced by the harness, so I cannot override it.
- **Logging hook:** every tool call is appended to `logs/tool-calls.log`. Only the tool name and query are logged, never email contents.
- **Asking first:** before any delete, spend, message, or write outside the repo, I ask you.

## 9. The Runable connection (the one uncertain piece)

Runable builds full-stack web apps with a database and logins. **I could not find public docs for a Runable API or scheduler**, so I have not assumed one exists.

**Getting new items into Runable**, from most reliable to most automated:
- **(a) File import.** I produce `items.json` and you upload or paste it into an "Import" box in the app [B p.15 suggests the same]. This works for sure and takes about 10 seconds.
- **(b) An "ingest" web address** in your Runable app that I send the file to with a secret key. This needs testing from this environment.

**Getting your state back to me:**
- **(a) CSV export.** You click Export and upload the file here.
- **(b) Automatic backup.** Runable saves a nightly backup to a Drive folder [B p.8], which I read (read-only).

**Decision:** you confirmed your Runable app can import a file and export a CSV, so that is the route (§12). The ingest address and the Drive backup stay optional upgrades. `runable/BUILD_SPEC.md` will be the text you paste into Runable's agent to build the app.

**Later and optional:** a scheduled Claude session every 7 days that runs "Run email" and saves memory. This only happens with your OK.

## 10. Your 8 capabilities → where they live

| Capability | Lives in |
|---|---|
| 1 Perception | `sensor.md` + `core/redact.py`, `core/ids.py` |
| 2 Memory | `memory/` + `core/memory.py` (read before, lesson after) |
| 3 Planning | Items with depends_on, gates, due dates and a risk note; plans are revised when you or the email change things |
| 4 Action | `core/dispatch.py` for scripts, the harness deny list + log for tools |
| 5 Critic | `critic.md` + `core/metrics.py` (the numbers come from code) |
| 6 Self-improvement | `skills/`, `config/`, `memory/knowledge/`, via the safe-change routine |
| 7 Sub-agents | `agents/` |
| 8 Metacognition | Confidence + unknowns stated at the start of every run; low confidence on a gated item means I ask you |

## 11. Build order

- **Phase 2:** memory, dispatch and logging, the read-only settings, `ids`, `redact`, and tests.
- **Phase 3:** gates, confidence, scoring, metrics and weekly modules; the role prompts; the Runable build spec; tests that reproduce A's worked example and the neutral golden set.
- **Phases 4-6:** the demo runs, the before/after comparison, and the README.

## 12. Your answers (2026-10-14)

| Question | Answer | Effect |
|---|---|---|
| Can your Runable app import a file and export a CSV? | Yes | File import in, CSV export out. No API is assumed. |
| Mark the top 3 at the head of the pending list? | No | The full pending list is ranked, with no top-3 marker. This overrides the Rule of 3 [A p.7; B p.5]. |
| Is a 7-day look-back right for the first run? | Do one same day, then every 7 days | Run 1 covers today's email only. After that, runs are every 7 days, each covering the 7 days since the last run. |
| Can you spend about 10 minutes correcting Run 1? | Yes | Your corrections are the labels for the before/after comparison. |
