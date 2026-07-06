# Round 3: Risks & Final Plan

Here’s the final execution plan.

I’m going to be blunt: the biggest risk is not extraction quality. It’s **silently damaging a system that just got better in R1–R4 by mixing schema changes, pipeline logic changes, and backfill in one motion**.

If you do this casually, you will:
- regress skill extraction without noticing for days,
- overwrite good existing data with lower-confidence parsed values,
- create Notion field inconsistency that becomes painful to unwind,
- burn CEO review time on low-value checks,
- and lose confidence in the benchmark because old/new logic got mixed.

So the final plan should be built around one principle:

## Core execution principle
**Do not mutate production behavior until you can compare old vs new side-by-side and roll back instantly.**

That means:
1. **Additive changes first**
2. **Pure extractors first**
3. **Shadow mode before cutover**
4. **Backfill only after sample validation**
5. **Never overwrite high-confidence existing values blindly**

---

# Executive decisions

## 1) Regression protection: yes, use old+new in parallel briefly
Not full permanent dual pipeline. That’s too heavy for a 2-person team.

But you **should version extraction behavior** for 1 week of shadow comparison:

- `pipeline_version = v1` = current R1–R4 behavior
- `pipeline_version = v2` = adds location/remote/rate changes

For forward processing:
- keep current production write path intact initially
- run new extractors in shadow mode
- store results separately or in non-authoritative fields/logs
- compare on sample before activating v2 writes

This is the cheapest way to protect R1–R4 gains.

### Minimum regression test
You do **not** need a giant test suite before moving.

You need 3 things only:

#### A. Golden set test
Create a fixed golden dataset of:
- 30 benchmark cases from Phase 0
- plus 20 known-good R1–R4 cases
- plus 10 ugly edge cases
= **60 total cases**

For each case, freeze expected outputs for:
- canonical skills
- skill empty/not empty
- status
- rate numeric/rate_type
- remote_type
- location
- timing if already extracted
- errors/NULL behavior

This becomes the non-regression gate.

#### B. No-degradation assertions
For the 60-case golden set:
- skill extraction empty rate must not worsen
- canonical skill count must not drop materially
- no previously valid fields become NULL unless expected
- parser must not throw exceptions on any record

#### C. Production diff check
Before cutover, run v1 + v2 on:
- last 50 recent emails / cases
Compare:
- skill output changed?
- status changed?
- parse failures increased?
If yes, stop and inspect.

If you skip this, you’ll ship a “location enhancement” that mysteriously breaks existing skill normalization through shared utility changes.

---

# Q1. Regression risk: exact answer

## How to protect R1–R4 gains
Use these safeguards:

### Safeguard 1: Freeze current extraction contract
Before changing anything:
- document current fields, function signatures, output formats
- snapshot current benchmark metrics
- tag current code as `pre_phase1_stable`

If you don’t tag it, rollback becomes guesswork.

### Safeguard 2: Extractors must remain pure
No direct Notion writes in extractor code.
Each extractor should be:
- input: raw text / structured input
- output: typed result object with confidence + method + raw evidence

That prevents side effects and makes testing easy.

### Safeguard 3: Separate extraction from write logic
You need:
- `extract_*()` functions
- `merge_*_into_record()` policy layer
- `persist_*()` layer

Why? Because the main corruption risk is not parsing. It is **bad merge rules** overwriting existing good values.

### Safeguard 4: Field-level overwrite policy
For each field:
- if existing value is high-confidence manual or prior trusted extraction, do not overwrite automatically
- only fill blanks or replace lower-confidence values
- record provenance

Example:
- existing `remote_type = "full_remote"` from manual review → preserve
- new extraction says `some_remote` with medium confidence → do not overwrite

### Safeguard 5: Shadow mode for 3–5 days
For forward pipeline:
- run v2 extraction results into audit log / temp fields
- do not use them for matching yet
- compare with current production

That’s enough. Full parallel matching is overkill now.

---

# Q2. Notion schema change risk: exact answer

## Can select/multi_select fields be added without breaking existing pages?
Yes, **adding new properties is generally safe** in Notion databases. Existing pages won’t break just because a new field exists.

What does go wrong:
- API property names drift because someone renames the field in UI
- select option values become inconsistent
- automations assume field exists immediately and fail on stale schema cache
- you repurpose existing fields and destroy historical meaning

## Safest way to add fields
**Add new fields. Do not repurpose old ones.**

Use additive schema only:
- `rate_type` (select)
- `remote_type` (select)
- `extraction_method` (select or rich_text; prefer select if bounded)
- `extraction_confidence` (number or select)
- `pipeline_version` (select/text)
- optionally `extraction_last_run_at` (date)
- optionally `extraction_review_needed` (checkbox)

### Why not reuse existing fields?
Because “using existing fields differently” is how semantics get corrupted.
You will forget six weeks later whether a blank means:
- not parsed yet,
- truly missing,
- parse failed,
- deferred to LLM,
- or incompatible old format.

That kills debugging and benchmarking.

## Recommended field design
Keep it simple.

### Required new properties
- `rate_type`:
  - `numeric`
  - `skill_dependent_no_number`
  - `skill_dependent_with_cap`
  - `unknown`
- `remote_type`:
  - `full_remote`
  - `partial_remote`
  - `onsite`
  - `unknown`
- `extraction_method`:
  - `regex`
  - `llm`
  - `manual`
  - `legacy`
- `extraction_confidence`:
  - number 0–100
- `pipeline_version`:
  - `v1`
  - `v2`

### Optional but very useful
- `backfill_batch_id`
- `last_extraction_error`
- `needs_review` checkbox

## Safest rollout for schema
1. Add fields manually in Notion first
2. Verify API can read/write them
3. Update code to tolerate missing fields gracefully anyway
4. Deploy write support only after read support works

Do **not** combine “create field + immediate mass backfill” in one task.

---

# Q3. Backfill safety: exact answer

This is where you are most likely to corrupt good data.

## Rules for safe backfill

### Rule 1: Backfill must be idempotent
Running it twice should not make data worse or duplicate anything.

### Rule 2: Never blind overwrite
Per-field merge rules:
- blank existing field → fill
- existing low-confidence auto value + new higher confidence → replace
- existing manual/high-confidence value → preserve
- conflicting values → mark `needs_review`, don’t overwrite

### Rule 3: Record before/after snapshots
At minimum log:
- page_id
- field_name
- old_value
- new_value
- reason
- extractor_method
- confidence
- timestamp
- batch_id

If rollback is needed, this log is your only lifeline.

### Rule 4: Batch it
Do **not** backfill all 469 at once.

Recommended batches:
- Batch 0: 20 cases
- Batch 1: 100 cases
- Batch 2: remaining ~349

Pause after each batch and inspect metrics.

### Rule 5: Dry-run mode first
Backfill command needs:
- `--dry-run`
- `--limit N`
- `--batch-id`
- `--only-empty-fields`
- optional `--page-ids`

If this doesn’t exist, you’re not ready.

## How to make backfill reversible
Strictly speaking, Notion doesn’t give you transactional rollback. So build operational rollback:

### Minimum rollback mechanism
A change log file / DB table:
- page_id
- changed properties
- prior values
- new values
- batch_id

Then implement:
- `rollback_backfill(batch_id)`

Even if semi-manual, it must exist before the first mass write.

If you skip rollback tooling because “we’ll be careful,” that’s amateur hour. You are changing 469 production records.

## Should backfill be all-at-once?
No.
Do:
1. 20-case dry-run + manual review
2. 20-case real write
3. 100-case write
4. remaining all at once only if metrics stable

---

# Q4. Cursor task granularity: exact answer

You want tasks that are:
- big enough to complete a meaningful unit,
- small enough that Cursor doesn’t lose context or mix concerns.

## Optimal number of tasks
For this plan: **8 tasks total**.

That is the sweet spot.
Less than 6 = too much bundled risk.
More than 10 = too much coordination overhead.

Each task should be **2–4 hours of Cursor work**, exactly as your constraint says.

---

# Final task list, order, dependencies, acceptance criteria

## Task 1 — Freeze baseline + golden test set
**Goal:** protect R1–R4 from regression before touching code.

**Dependencies:** none

**Work:**
- tag current pipeline `pre_phase1_stable`
- create 60-case golden dataset:
  - 30 mini-benchmark
  - 20 known-good R1–R4
  - 10 edge/failure cases
- serialize expected outputs in test fixtures
- record baseline metrics

**Acceptance criteria:**
- git tag or release snapshot exists
- test fixture file exists for 60 cases
- baseline metrics document exists
- a single command can run regression checks

**CEO review needed?**
No.

---

## Task 2 — Add Notion schema safely
**Goal:** additive schema only, no behavior change.

**Dependencies:** Task 1

**Work:**
- add new Notion properties:
  - rate_type
  - remote_type
  - extraction_method
  - extraction_confidence
  - pipeline_version
  - needs_review
- update schema access code to handle absent fields gracefully
- add a schema verification script

**Acceptance criteria:**
- script confirms all required properties exist
- reading old pages still works
- writing a test page with new fields works
- no production pipeline logic changed yet

**CEO review needed?**
No, unless CEO manually owns Notion admin access. If so, 10-minute approval only.

---

## Task 3 — Implement pure rate/remote/location extractors
**Goal:** new extraction logic isolated from pipeline.

**Dependencies:** Task 1

**Work:**
- implement `extract_rate()`
  - regex pass
  - true-empty => NULL
  - LLM fallback hook only, not bulk execution yet
- implement `extract_remote()`
  - regex-first
  - ambiguous classification
- implement `extract_location()`
- output typed result object:
  - value
  - rate_type/remote_type
  - method
  - confidence
  - raw evidence
  - review_needed

**Acceptance criteria:**
- extractors are pure functions
- all golden tests pass for existing R1–R4 outputs
- new fields extract on fixture set
- no Notion writes in extractor module

**CEO review needed?**
No.

---

## Task 4 — Merge policy + backfill dry-run engine
**Goal:** prevent corruption during writes.

**Dependencies:** Tasks 2, 3

**Work:**
- implement field-level merge rules
- implement backfill command with:
  - dry-run
  - batch-id
  - page limit
  - only-empty-fields
  - change logging
- implement rollback helper from change log

**Acceptance criteria:**
- dry-run outputs before/after changes without writing
- write mode creates change log with reversible payload
- manual/high-confidence values are preserved by policy
- test cases cover overwrite/no-overwrite paths

**CEO review needed?**
No.

---

## Task 5 — Shadow mode integration into forward pipeline
**Goal:** run new extraction on incoming records without changing matching behavior.

**Dependencies:** Tasks 2, 3, 4

**Work:**
- integrate v2 extraction into mail pipeline
- write results to new fields / audit log
- preserve current matching input behavior
- stamp `pipeline_version`
- add error handling + metrics

**Acceptance criteria:**
- incoming records process successfully
- old matching still runs unchanged
- new extracted fields populate on new records
- regression suite passes
- no increase in pipeline exceptions

**CEO review needed?**
Yes — first meaningful checkpoint.

### CEO Checkpoint 1
Review 10–15 recent shadow-mode records:
- rate_type sane?
- remote_type sane?
- location sane?
- obvious false positives?
If this is bad, stop before backfill.

Time required: 20–30 min.

---

## Task 6 — 20-case backfill pilot + ERROR retry framework
**Goal:** validate write safety on production data.

**Dependencies:** Task 5 + CEO Checkpoint 1

**Work:**
- run dry-run on 20 selected active cases
- review diffs
- execute real write on same 20
- implement ERROR retry path for extractor failures
- mark retry candidates separately from parse-null

**Acceptance criteria:**
- 20-case backfill completed
- change log recorded
- rollback tested on at least 1 case
- no overwritten good values found in sample
- ERROR retry path distinguishes:
  - parse error
  - true empty
  - ambiguous requiring LLM/manual

**CEO review needed?**
Yes.

### CEO Checkpoint 2
Review the 20-case pilot diff summary only, not all implementation:
- # fields filled
- # conflicts skipped
- # needs_review
- 5 sampled records before/after

Time required: 20 min.

---

## Task 7 — Batch backfill 100 → remaining 349
**Goal:** complete historical backfill safely.

**Dependencies:** Task 6 + CEO Checkpoint 2

**Work:**
- run 100-case batch
- inspect metrics
- if stable, run remaining ~349
- throttle LLM fallback under budget
- produce final backfill report

**Acceptance criteria:**
- all batches logged by batch_id
- conflict rate reported
- rollback possible by batch_id
- no spike in write failures
- LLM usage within daily cap

**CEO review needed?**
No, unless conflict rate exceeds threshold.

### Auto-stop thresholds
If any occur, stop and escalate:
- >5% of records flagged `needs_review`
- >2% write failures
- any evidence of manual/high-confidence overwrite
- skill extraction metrics worsen on fresh records

---

## Task 8 — Matching hard filters activation
**Goal:** use new fields in matching, in agreed order.

**Dependencies:** Tasks 5 and 7 complete, stable metrics

**Work:**
- implement hard filters in order:
  1. status
  2. rate
  3. remote/location
  4. skill
  5. experience
  6. timing
- add per-filter drop-off metrics
- run mini-benchmark comparison before turning on fully

**Acceptance criteria:**
- benchmark shows expected precision lift
- filter-level metrics visible
- no unexplained candidate collapse
- can toggle filters via config flags

**CEO review needed?**
Yes.

### CEO Checkpoint 3
This is the final approval before matching behavior changes.
Review:
- mini-benchmark results
- candidate count before/after
- false negative examples
- whether rate/location filtering feels too strict

Time required: 30–45 min.

---

# Recommended sequencing by week

## Day 1–2
- Task 1
- Task 2

## Day 3–4
- Task 3

## Day 5
- Task 4

## Week 2, Day 1
- Task 5
- CEO Checkpoint 1

## Week 2, Day 2–3
- Task 6
- CEO Checkpoint 2

## Week 2, Day 4–5
- Task 7

## Week 3
- Task 8
- CEO Checkpoint 3

This is realistic for Cursor + a small team.

---

# Q5. CEO review bottleneck: exact answer

You should use CEO time only where product judgment matters, not engineering verification.

## Require CEO review
Only 3 points:

### 1. Shadow mode sample review
Because only CEO can tell if extracted business semantics are acceptable.

### 2. 20-case backfill pilot review
Because this is the first production write risk.

### 3. Matching hard-filter activation
Because this changes business output and false negatives matter.

That’s it.

## No CEO review needed
Can be fully autonomous:
- regression harness
- schema additions
- pure extractor implementation
- merge policy implementation
- dry-run tooling
- rollback tooling
- batch execution, if thresholds look safe
- cost monitoring

## Minimum CEO touchpoints
**Three touchpoints total**
- 20–30 min
- 20 min
- 30–45 min

Total: under 2 hours across 3 weeks.

If CEO gets pulled into every task, execution will drag and quality will still not improve.

---

# Q6. CostGuard budget: exact answer

You asked for cost estimate for:
- ERROR retry for 1,509 records
- LLM fallback for rate/remote

The good news: if you keep regex-first and only send ambiguous cases, this is likely affordable.

## Main budgeting assumption
You have:
- remote extractable via regex: 70.4%
- LLM for <15% ambiguous
- rate LLM fallback for only 6 benchmark cases, but production may be higher

Let’s estimate conservatively.

## Estimated LLM volumes

### Remote LLM fallback
For 469 active backfill:
- 15% ambiguous ≈ 70 records

For 1,509 ERROR retry:
- worst case do not send all to LLM
- many ERRORs will be non-remote-related
- assume 15% remote ambiguity among retry candidates ≈ 226 records

Total remote LLM cases ≈ **296**

### Rate LLM fallback
If truly only difficult edge cases:
- assume 5–10% of records need LLM after regex/NULL logic

For 469 active:
- 5% = 23
- 10% = 47

For 1,509 retry:
- 5% = 75
- 10% = 151

Total rate LLM cases ≈ **98 to 198**

### Combined estimated LLM cases
Roughly:
- low: 394
- high: 494

Round to **~400–500 LLM calls**

## Cost estimate
Actual cost depends on model and token size, but extraction prompts are short.

If each call is a small structured extraction:
- likely **a few cents per 10–20 calls**, not dollars per call
- total project cost probably in the **single-digit to low tens of dollars**, not hundreds

A realistic range:
- **$5–$20 total** if prompts are compact and model is cheap
- maybe **$20–$40** if prompts are sloppy and you send huge email bodies

## Will it fit CostGuard?
Yes, **if you phase it**.
No, if you:
- send full raw emails unnecessarily,
- retry all 1,509 blindly in one day,
- or use a large expensive model for trivial extraction.

## How to stay under $8/day
Use this phasing:

### Day budget rules
- cap LLM extraction to **100–150 calls/day**
- prioritize:
  1. active 469 backfill
  2. new incoming records
  3. old ERROR retry backlog last

### Prompt optimization
Send only the relevant text span:
- rate lines
- remote lines
- location lines
Not full email body unless necessary.

### Retry tiers
For ERROR backlog:
1. rerun regex/parser only
2. only unresolved ambiguous cases go to LLM
3. unresolved after LLM => review queue / leave unknown

### Hard cap
Implement config:
- `MAX_LLM_EXTRACTIONS_PER_DAY`
- `MAX_LLM_RETRIES_PER_RUN`

Without hard caps, “temporary retry logic” will quietly eat your budget.

---

# Q7. What you’re still likely wrong about

Here’s what you are still underestimating.

## 1. The hard part is merge policy, not extraction
You’re still thinking in extractor terms.
The real production risk is:
- when to overwrite,
- when to preserve,
- what confidence means,
- and how to avoid turning “unknown” into bad certainty.

This is the #1 place small systems get corrupted.

## 2. Notion is not a real transactional data store
You are treating backfill like a normal migration. It isn’t.
Notion will let you:
- partially update records,
- hit API weirdness,
- suffer field naming drift,
- and rollback painfully.

So your migration discipline must be stricter than usual.

## 3. Hard filters will create false negatives faster than expected
Rate/location/remote hard filters sound clean, but real SES data is messy:
- “週3リモート”
- “地方可だが初月出社”
- “スキル見合い 75万まで”
- “東京近郊”
- “面談即日可”
If you go hard too early without measuring drop-off, you will reject good matches.

## 4. ERROR backlog is heterogeneous garbage
The 1,509 ERROR cases are not one problem.
Some are:
- malformed text
- parser bugs
- upstream formatting issues
- weird templates
- true missing information
If you attack them as one retry batch, results will be noisy and hard to interpret.

## 5. CEO sampling can give false confidence
If CEO reviews 5 good-looking examples, that proves almost nothing.
Use structured sampling:
- obvious easy case
- ambiguous remote case
- no-rate case
- capped skill-dependent rate case
- location edge case

Otherwise checkpoint reviews become ceremony.

---

# The #1 thing that will go wrong during execution

## You will accidentally overwrite “good enough” existing data with lower-quality normalized values during backfill.

That is the most likely failure.

Not because the extractor is terrible.
Because your code will do something like:
- existing field present but non-standard
- new parser returns normalized but wrong-ish value
- automatic write replaces it
- nobody notices until matching quality shifts

### Prevent this with one hard rule:
**Backfill may fill blanks by default. Replacement of non-blank existing values must require stronger confidence or explicit policy.**

If you follow only one thing from this whole plan, follow that.

---

# Final concrete operating rules

Use these as execution guardrails starting tomorrow.

## Guardrail 1
No task may both:
- change extraction logic
- and perform production backfill
in the same deployment step.

## Guardrail 2
No mass write without:
- dry-run
- diff log
- batch-id
- rollback path

## Guardrail 3
No matching logic activation until:
- shadow mode sample reviewed
- 20-case backfill pilot passed
- golden set non-regression passed

## Guardrail 4
LLM is fallback only.
Never default to LLM when regex/structured parse is enough.

## Guardrail 5
Preserve unknowns.
A clean `unknown` is better than a wrong hard filter input.

---

# Final recommended execution plan

## Start tomorrow with this exact order
1. **Task 1** baseline freeze + golden set
2. **Task 2** additive Notion schema
3. **Task 3** pure extractors
4. **Task 4** merge policy + dry-run/rollback
5. **Task 5** shadow mode forward integration
6. **CEO Checkpoint 1**
7. **Task 6** 20-case backfill pilot + ERROR retry framework
8. **CEO Checkpoint 2**
9. **Task 7** staged backfill 100 → 349, throttled LLM
10. **Task 8** matching hard filters activation
11. **CEO Checkpoint 3**

---

# If you want the shortest possible “do not screw this up” summary

- **Add fields, don’t repurpose fields**
- **Version behavior briefly in shadow mode**
- **Freeze a 60-case golden set before touching code**
- **Backfill in 20 → 100 → rest**
- **Default policy: fill blanks, don’t overwrite non-blank**
- **Keep LLM capped and fallback-only**
- **Use CEO only for three business-judgment checkpoints**
- **Don’t activate hard filters until benchmark confirms no candidate collapse**

If you want, I can turn this into the actual `pending_tasks/` markdown files next, one by one with exact Cursor instructions and acceptance checklists.