# Round 1: Priority & Dependencies

Your current order is not quite right. You’re mixing **business impact**, **measurement**, and **cleanup** in a sloppy way.

## Blunt verdict

- **Phase A → B → C is directionally right**
- But your **contents inside each phase are wrong**
- And putting **benchmark set in Phase C is a mistake**
- Also, **ERROR retry and KPI cohort separation should be split** — they are not one thing

---

# The real priority logic

You have 3 different job types here:

1. **Make metrics trustworthy**
2. **Fix high-leverage structured data used by matching**
3. **Improve nice-to-have extraction quality**

You’re currently blending them.

That’s how teams waste a week “improving quality” and then realize they still can’t prove anything improved.

---

# Correct order

## Phase 0 — Measurement hygiene first
Do these before major extraction work:

### 0.1 KPI cohort separation — immediately
This should **not** be in cleanup.

Why:
- 48.3% of matching records being ERROR means your top-line metrics are polluted
- You already know these come from a legacy 6/5 bug
- If you don’t separate legacy-bug records from current-pipeline records, every metric discussion is half-fake

This is not optional.  
This is not cleanup.  
This is **instrumentation**.

What to do:
- Split dashboard/reporting into:
  - **Legacy cohort**
  - **Current pipeline cohort**
- Stop quoting blended metrics

You do **not** need to retry the 1,509 records yet.  
You **do** need to stop letting them contaminate decision-making.

---

### 0.2 Minimal benchmark first — not full 100-case, but not zero either
Your current “benchmark set in Phase C” is wrong.

Without ground truth, you are basically grading yourself with your own parser output. That’s useless.

But a full 100-case benchmark before all work? That’s probably overkill for a 2-person shop with limited CEO review time.

## Correct move:
Create a **lean benchmark first**:
- 20–30 representative cases
- Stratified across:
  - rate ranges / ambiguous rate forms
  - remote patterns
  - location present/absent
  - preferred skills present
  - known bad legacy cases if relevant

Then later expand to 100.

So:
- **Mini benchmark now**
- **100-case formal benchmark later**

That avoids both extremes:
- not blind
- not over-engineering

If you skip this, you will ship extraction changes and have no idea whether you improved precision or just increased fill rate.

---

# Phase 1 — Fix data fields that directly unlock matching
This is where your current ordering needs the most correction.

Your proposed Phase A includes:
- Rate reparse
- Remote extractor
- Location integration
- Preferred skills enhancement

That’s not the right sub-order.

## Correct sub-order for Phase 1:

### 1) Location extractor integration
This should be first among extraction tasks.

Why:
- It is already built
- It is low-risk
- It is pipeline wiring only
- It likely gives immediate structured-data lift with minimal review burden

You have a 2-person team and limited CEO testing time.  
That means you should front-load **cheap, deterministic wins**, not jump straight to LLM-heavy repair.

If something is “already built but not wired,” and you don’t do it first, that’s bad prioritization.

---

### 2) Remote extractor
Do this next.

Why:
- Currently 0% populated
- Source data clearly exists
- High matching value
- Likely rule/pattern-driven, not expensive
- Strong business relevance: remote/onsite is a major staffing filter

This is more important than preferred skills by a mile.

---

### 3) Rate 0万 reparse
Yes, this is major.  
But I would put it **after** location integration and remote extraction, not before both.

Why:
- It is one-off repair + probably the riskiest implementation in this phase
- It likely uses LLM re-extraction and therefore needs more care
- It fixes a high-visibility quality bug, but it’s not the cheapest first win
- You want a couple of fast successful deploys before burning cycles on a reparse operation

That said: it is still **higher priority than preferred skills**.

Also important: this should not be framed as just “improve true quality metric.”  
It affects:
- rate-based filtering
- scoring
- credibility of structured data
- potential salary/rate matching precision

So yes, high priority. Just not necessarily first **implementation** item.

---

### 4) ERROR retry/reprocess — after extraction fixes are in
This is where your dependency logic is off.

You bundled:
- ERROR retry/purge
- KPI cohort separation

Those should be separated.

## Retry should happen after extraction fixes
Why:
- If you reprocess 1,509 records **before** deploying improved rate/location/remote extraction, you’ll likely need to touch them again later
- That is wasted compute and wasted operational churn
- You want legacy records to benefit from the fixed pipeline when you re-run them

So:
- **Separate the cohort now**
- **Retry/reprocess later, after core extractors are fixed**

That’s the correct dependency.

---

# Phase 2 — Matching quality
Now you can do matching work.

## 5) Matching hard filters
This is correctly placed after rate/location/remote.

You already understand the dependency:
- hard filters need clean structured data

But I’ll be harsher:  
If you build hard filters before cleaning those 3 fields, you’re building a false sense of precision on broken inputs.

Hard filtering on bad data is worse than loose matching, because:
- bad data becomes false negatives
- users stop seeing viable candidates/jobs
- trust drops faster than with high recall / low precision

So yes, this belongs after those field fixes.

---

### 6) Rate/location/remote-aware scoring
After hard filters, yes.

Reason:
- hard filters cut volume
- scoring ranks within the reduced set
- doing scoring first while average matches are 128.5 is lipstick on a pig

You don’t rank your way out of a terrible candidate set size.  
You first cut obvious mismatches.

---

# Phase 3 — Secondary extraction improvements
Now the things you overvalued a bit:

### 7) Preferred skills enhancement
This should **not** be ahead of matching hard filters.

Why:
- preferred skills are usually softer relevance signals
- they don’t seem to be gating anything
- they improve richness, not core precision
- going from 62% empty to 30–40% sounds nice, but that is not as valuable as fixing the 128.5 average match explosion

This belongs after core matching data and filters.

You’re currently giving it too much importance because the percentage movement looks dramatic.  
That’s vanity metric thinking.

---

### 8) Required skills LLM fallback
Correctly low priority.

26 cases is tiny.  
This is floor polishing.

Do it later unless:
- those 26 are disproportionately high-value records
- or it’s nearly free to implement

Otherwise, no.

---

# Revised priority order

## Best practical order

### Phase 0: measurement / control
1. **KPI cohort separation**
2. **20–30 case mini benchmark**

### Phase 1: core data fixes for matching
3. **Location extractor integration**
4. **Remote extractor**
5. **Rate 0万 reparse**
6. **Reprocess/retry legacy ERROR records using the improved pipeline**

### Phase 2: matching
7. **Matching hard filters**
8. **Rate/location/remote-aware scoring**

### Phase 3: secondary quality improvements
9. **Preferred skills enhancement**
10. **Required skills LLM fallback**
11. **Expand mini benchmark to full 100-case set**

If you insist on keeping exactly the original 8 buckets, then the ordering should be:

1. **KPI cohort separation**  
2. **Mini benchmark subset of the 100-case benchmark**  
3. **Location extractor integration**  
4. **Remote extractor**  
5. **Rate 0万 reparse**  
6. **ERROR retry/reprocess**  
7. **Matching hard filters**  
8. **Rate/location/remote-aware scoring**  
9. **Preferred skills enhancement**  
10. **Required skills fallback**  
11. **Full 100-case benchmark expansion**

---

# Direct answers to your questions

## 1. Is Phase A→B→C ordering correct? Should anything move?
**Mostly yes at the phase level, no at the task level.**

### Move these:
- **KPI cohort separation must move to the front**
- **Benchmark must move earlier**
- **Preferred skills should move later**
- **ERROR retry should move earlier than you placed it, but only after extraction fixes**
- **Location integration should come before rate reparse**
  
Your current plan over-prioritizes “interesting extraction improvements” and under-prioritizes **measurement integrity** and **cheap deterministic wins**.

---

## 2. Should benchmark set come FIRST?
### Full 100-case benchmark first?
**No.**
That’s probably too heavy for your review bandwidth.

### Some benchmark first?
**Yes. Absolutely.**
Do a **20–30 case mini benchmark** first.

Calling benchmark-first “perfectionism” is lazy rationalization if you currently have **zero ground truth**.

No benchmark means:
- you can measure fill rate
- you cannot measure correctness well
- you can’t detect regressions confidently
- you will fool yourself

So the right answer is:
- **not full benchmark first**
- **but definitely some benchmark first**

---

## 3. Within Phase A, what's the right sub-order?
Your proposed sub-order is not ideal.

## Correct sub-order:
1. **Location extractor integration**
2. **Remote extractor**
3. **Rate 0万 reparse**
4. **Preferred skills enhancement**

Why:
- location integration is lowest-risk/highest-certainty
- remote is high-value structured matching data
- rate reparse is major but heavier/riskier
- preferred skills is not gating matching quality

If you want an alternate order, the only defensible swap is:
- **Rate reparse before remote**
  
That would make sense if your immediate pain is bad rate filtering/scoring rather than remote constraints.  
But I would still not put preferred skills above either.

---

## 4. Can 168 rate reparses fit in the $8/day budget?
Almost certainly yes.

Your current spend is **$16.35/month**, which is tiny relative to your **$140/month cap**.

You’re using only **11.7% of monthly budget**.  
So financially, this is not the bottleneck.

The real bottleneck is not money.  
It’s:
- implementation correctness
- batch retry safety
- QA time
- making sure you don’t parse garbage confidently

### Rough practical answer:
168 reparse calls is unlikely to threaten your budget unless:
- prompts are absurdly large
- you’re using an unnecessarily expensive model
- you rerun them repeatedly due to poor batching/retry design

Even if each case required a full LLM extraction call, you have plenty of budget headroom.

### Better operational advice:
- batch them over 2–4 days
- log before/after values
- sample-review 20 outputs manually
- make the reparse idempotent and reversible

Budget is not the scary part here.  
Blindly mass-updating production values is.

---

## 5. Am I making any dependency errors?
Yes.

## Dependency error #1:
You treated **KPI cohort separation** and **ERROR retry** as one bundle.

They are different:
- **cohort separation** = immediate measurement hygiene
- **retry** = data remediation job after pipeline fixes

Don’t conflate them.

---

## Dependency error #2:
You put **benchmark** too late.

Benchmark is not a cleanup artifact.  
It is a control mechanism.

No benchmark = weak feedback loop.

---

## Dependency error #3:
You are implicitly treating **preferred skills** as if it’s upstream of matching quality.
It isn’t, at least not for your stated hard-filter objective.

Hard filters depend on:
- rate
- location
- remote

Not on preferred skills.

---

## Dependency error #4:
If you retry the 1,509 ERROR records before deploying extraction fixes, you risk double work.

Correct dependency:
- deploy extraction improvements
- then reprocess legacy failures through the improved pipeline

---

## 6. What’s the single most important thing I should NOT skip?
If I have to pick one:

# **Do not skip KPI cohort separation.**

Why this over benchmark?
Because right now your dashboard is actively misleading you due to known legacy contamination.

You can survive briefly with a small benchmark gap.  
You should not keep making decisions on blended metrics that you already know are corrupted.

### Close second:
**Do not skip a mini benchmark before/alongside the extraction changes.**

If you ask me what one thing most teams skip and regret: benchmark.  
If you ask me what one thing is currently making your metrics dishonest: cohort separation.

So:
- **Most urgent not-to-skip:** KPI cohort separation
- **Most strategically dangerous to skip:** mini benchmark

---

# What I think you’re underestimating

## 1. Cheap integration work beats glamorous parser work
You have a small team and limited review time.  
That means your first moves should be:
- low-risk
- testable
- structurally important

“Extractor already built but not wired” should light up your board as a near-immediate action.

---

## 2. Preferred skills is a distraction right now
You’re overreacting to the “62% empty” number.

Empty preferred skills is not your main matching problem when:
- remote is 0%
- location is 29.1% empty
- rate has systematic corruption
- average matches are 128.5
- half of matching records are legacy ERRORs

Preferred skills is a phase-later enrichment task, not an early battlefield objective.

---

## 3. Retry timing matters
If you fix legacy errors too early, you reprocess bad logic.  
If you fix them too late, your clean corpus stays small.

So the timing is:
- **after core extraction fixes**
- **before final matching KPI evaluation**

That’s the sweet spot.

---

# Final recommended plan

## Week 1
1. **KPI cohort separation**
2. **20–30 case mini benchmark**
3. **Location extractor integration**
4. **Remote extractor**
5. **Rate 0万 reparse**

## Week 2
6. **Reprocess/retry 1,509 legacy ERROR records through improved pipeline**
7. **Matching hard filters**
8. **Rate/location/remote-aware scoring**

## Week 3 / later
9. **Preferred skills enhancement**
10. **Required skills LLM fallback**
11. **Expand mini benchmark to full 100-case set**

---

# Bottom line

Your current plan is **close structurally but wrong in the details**.

## The biggest corrections:
- **Benchmark does not belong in Phase C**
- **KPI cohort separation must happen first**
- **Location integration should be earlier**
- **Preferred skills should be later**
- **ERROR retry should happen after extraction fixes, not as random cleanup**

If you want, I can turn this into a **task-by-task execution board** with:
- exact task order
- dependencies
- expected effort in “Cursor instruction files”
- CEO review checkpoints
- rollback/risk notes for each item.