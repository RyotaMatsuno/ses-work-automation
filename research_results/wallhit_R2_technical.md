# Round 2: Technical Approach

Here’s the blunt recommendation set for Round 2.

---

# Executive answer

Your instinct is mostly right, but tighten it:

- **Q1 rate 0万**: **Do not use LLM for all 168.** Use a **deterministic 3-pass parser**:
  1. regex extraction for numeric rate patterns,
  2. explicit normalization of true-missing to `NULL`,
  3. LLM fallback only for unresolved-but-rate-mentioned cases.
- **Q2 remote**: **Regex first, LAG/LLM fallback only for ambiguous “リモート” cases**, not full LLM on all.
- **Q3 hard filters**: Apply in this order:
  1. **must-have exclusions**: closed/expired, employment type mismatch, nationality/security constraints, start date impossible
  2. **rate compatibility**
  3. **location/remote compatibility**
  4. **required skill threshold**
  5. optional: age/role seniority/vendor constraints if legally/operationally acceptable
- **Q4 integration**: **Both**. Backfill old records and wire into forward pipeline immediately. Otherwise your benchmark and daily matching stay polluted.
- **Q5 スキル見合い**: store as **`rate_type = skill_dependent`** and **`rate_max` if extractable**, else `NULL`. Do **not** estimate rates from skills.
- **Q6 mini benchmark**: annotate **30 cases**, stratified by pattern type, with exact gold labels for `rate_min`, `rate_max`, `rate_type`, `remote_type`, `location`, `required_skills`, and matching eligibility. Score field-level precision/recall plus “filter decision correctness.”

Now the detailed technical approach.

---

# Q1: Rate 0万 fix — exact approach

## Recommendation
Use **three-step deterministic-first processing**, not LLM-for-all.

### Why not LLM for all 168?
Because consistency is not your main risk. **False confidence is.**
If you send all 168 to LLM:
- you spend more,
- you create non-deterministic outputs,
- you increase drift risk,
- and you blur the distinction between:
  - **extractable numeric rate**,
  - **explicitly skill-dependent/no numeric rate**,
  - **truly absent rate info**.

For matching, those are different states and should remain different.

---

## Correct data model for rate

Add these fields if you don’t already have them:

```python
rate_min_man: number | null
rate_max_man: number | null
rate_text_raw: string | null
rate_type: enum[
  "fixed_range",
  "fixed_upper_only",
  "fixed_lower_only",
  "skill_dependent_with_cap",
  "skill_dependent_no_number",
  "unknown",
  "not_present"
]
rate_extraction_method: enum["regex", "llm", "manual", "legacy"]
rate_confidence: float  # 0.0 - 1.0
```

Do **not** store `0` as a semantic value. `0` is a data corruption state here.

---

## Processing logic

## Pass 1: regex extraction
Target the recoverable 60 first.

### Regex classes
Process in order:

### 1. skill-dependent with MAX
Examples:
- `スキル見合い（MAX65万）`
- `スキル見合い Max 70万`
- `スキル見合い、上限75万円`

Pattern sketch:
```regex
スキル見合い.*?(?:MAX|上限|～|〜)?\s*(\d{2,3})\s*万
```

Output:
```json
{
  "rate_min_man": null,
  "rate_max_man": 65,
  "rate_type": "skill_dependent_with_cap",
  "rate_confidence": 0.98
}
```

### 2. range
Examples:
- `60〜70万`
- `60-70万`
- `60～70万円`
- `65万～75万`

Pattern:
```regex
(\d{2,3})\s*(?:万|万円)?\s*[〜～\-~]\s*(\d{2,3})\s*万(?:円)?
```

Normalize if reversed.

Output:
`fixed_range`

### 3. max only
Examples:
- `MAX 70万`
- `上限70万円`
- `〜70万`
- `70万円まで`

Patterns:
```regex
(?:MAX|上限|まで|～|〜)\s*(\d{2,3})\s*万
```

Output:
`fixed_upper_only`

### 4. plain number
Examples:
- `65万`
- `単価: 75万円`

Pattern:
```regex
(?:単価|予算|金額)?[:：]?\s*(\d{2,3})\s*万(?:円)?
```

Output:
This is ambiguous between fixed point and upper bound. For SES, safest storage:
```json
{
  "rate_min_man": null,
  "rate_max_man": 65,
  "rate_type": "fixed_upper_only",
  "rate_confidence": 0.75
}
```

Unless source explicitly says `65万固定`, then use both min=max=65 and `fixed_range`.

---

## Pass 2: true missing → NULL
For the **118 cases with no rate data in source**:

Set:
```json
{
  "rate_min_man": null,
  "rate_max_man": null,
  "rate_type": "not_present",
  "rate_confidence": 1.0
}
```

And importantly:
- overwrite legacy `0`
- preserve original source text for audit

Do **not** leave `0` anywhere in matching code. `0` will poison hard filters.

---

## Pass 3: LLM only for unresolved-but-mentioned
Use LLM only for the **6 “budget word but unclear”** and any regex misses where rate-related text exists.

### LLM prompt should not be open-ended
Use constrained extraction:

```json
{
  "rate_mentioned": true/false,
  "rate_min_man": number|null,
  "rate_max_man": number|null,
  "rate_type": "fixed_range|fixed_upper_only|fixed_lower_only|skill_dependent_with_cap|skill_dependent_no_number|unknown|not_present",
  "evidence_span": "exact substring from source"
}
```

And reject hallucinations:
- if no direct evidence substring, do not accept extraction.

---

## Implementation recommendation
Run this as a **one-time migration script** plus reusable library.

### Suggested module
```python
# extractors/rate_extractor.py
def extract_rate(text: str) -> dict:
    ...
```

### Suggested migration script
```python
# scripts/backfill_rate_zero.py
for case in notion_cases_with_rate_zero():
    result = extract_rate(case["source_text"])
    update_case(case["id"], result)
```

---

# Q2: Remote extractor — regex vs LLM

## Recommendation
Use **c) regex first, LLM fallback for ambiguous cases**.

But I’d sharpen that further:
- **Regex for all**
- **No LLM for obvious full/hybrid/onsite**
- **Optional LLM only for texts containing “リモート/テレワーク” without enough qualifiers**
- For “no mention,” keep as `unknown` or `not_present`, not LLM-guessed

---

## Why not pure regex only?
Because Japanese remote wording is messy:
- `リモート併用`
- `立ち上がり出社、その後リモート`
- `週1出社`
- `地方在住可`
- `初日出社`
- `フルリモート可(地方不可)`
- `基本リモート`
- `出社メイン`

Pure regex will work for the majority, but it will misclassify nuanced operational constraints that matter for matching.

## Why not LLM for all 469?
Wasteful and unstable. You already know **70.4% is regex-extractable**. Don’t pay for a language model to rediscover “常駐”.

---

## Exact remote data model

```python
remote_type: enum[
  "full_remote",
  "hybrid",
  "onsite",
  "remote_possible_unspecified",
  "unknown"
]

remote_days_per_week_min: int | null
remote_days_per_week_max: int | null
initial_onsite_required: bool | null
location_constraint_text: string | null
remote_evidence: string | null
remote_extraction_method: enum["regex", "llm", "manual"]
remote_confidence: float
```

Important: I would **not** use both `unknown` and `none` as separate categories unless your semantics are very strict.

Use:
- `unknown` = no reliable classification / no mention
- `onsite` = explicitly non-remote /常駐 / 出社前提

If you use `none`, people will confuse it with “no remote allowed.” Avoid that.

---

## Regex rule order

Order matters.

### 1. Explicit onsite
Keywords:
- `常駐`
- `オンサイト`
- `出社前提`
- `基本出社`
- `フル出社`

If matched, classify `onsite` unless text also clearly says hybrid/full remote.

### 2. Explicit full remote
Keywords:
- `フルリモート`
- `完全リモート`
- `在宅100%`
- `出社なし`

### 3. Hybrid
Patterns:
- `週\d+出社`
- `リモート併用`
- `ハイブリッド`
- `一部出社`
- `基本リモート.*出社`
- `出社.*リモート併用`

Also parse counts:
```regex
週\s*(\d)\s*日?\s*出社
```

### 4. Ambiguous remote possible
Keywords:
- `リモート`
- `テレワーク`
- `在宅`
without frequency/context

Classify:
`remote_possible_unspecified`

### 5. Unknown
No location mode mention.

---

## LLM fallback trigger
Only send to LLM if:
- regex matched conflicting categories, or
- text contains both remote and onsite indicators, or
- text has special constraints:
  - `立ち上がり1ヶ月出社後リモート`
  - `地方不可`
  - `初日のみ出社`
  - `緊急時出社`

This is probably **<15%** of cases.

---

# Q3: Matching hard filters — exact filters and order

Current average 128.5 matches is too high unless your supply side is tiny. You need aggressive pruning before scoring.

## Recommended hard filter order

Apply cheapest/high-confidence filters first.

---

## Filter 0: status gate
Exclude cases that are:
- closed
- expired
- duplicated
- clearly inactive

If you don’t have status normalization, add it.

---

## Filter 1: employment / contract eligibility
Hard reject if:
- candidate contract type incompatible with case
- required nationality/work authorization not satisfied
- required clearance/security not satisfied
- required Japanese level not met if explicit

These are true hard blockers.

Fields:
```python
contract_type
nationality_requirement
work_auth_required
jp_level_required
security_clearance_required
```

If these are absent, skip; do not infer.

---

## Filter 2: rate compatibility
This should be a hard filter, but with care around unknowns.

## Candidate side assumption
You need candidate desired rate:
```python
candidate_rate_min_man
candidate_rate_target_man
```

## Case side rules
- If case has `rate_max_man` and candidate min > case max + tolerance: reject
- If case has no rate: do not reject
- If case is `skill_dependent_no_number`: do not reject, but add uncertainty penalty in scoring

### Tolerance
Use `+3万` or `+5%`, whichever is larger.

Example:
```python
if case.rate_max_man is not None and cand.rate_min_man is not None:
    if cand.rate_min_man > case.rate_max_man + 3:
        reject
```

Reason: recruiter-entered rates and mail-parsed rates are noisy.

---

## Filter 3: location / remote compatibility
This should be hard only when explicit.

## Candidate fields needed
```python
candidate_remote_preference: enum["full_remote_only","hybrid_ok","onsite_ok"]
candidate_commutable_locations: list[str]
candidate_max_onsite_days_per_week: int | null
```

## Rules
### Reject if:
- case `onsite` and candidate `full_remote_only`
- case location not commutable and remote not sufficient
- case requires weekly onsite beyond candidate tolerance

### Do not reject if:
- case remote unknown
- location vague
- candidate flexibility unclear

This filter can eliminate a lot of nonsense matches.

---

## Filter 4: required skill threshold
This is the biggest one.

But don’t do naive word overlap. Use normalized required skills.

## Skill normalization
Create a skills dictionary:
- `Java`, `Java8`, `Java11` => `java`
- `AWS`, `Amazon Web Services` => `aws`
- `React.js`, `React` => `react`
- `SpringBoot`, `Spring Boot` => `spring_boot`

Then split into:
```python
required_skills_normalized: list[str]
preferred_skills_normalized: list[str]
```

## Hard rule
If case has **2+ required skills**, require:
- at least **1 exact core skill hit**, and
- **required_skill_match_ratio >= 0.5** for technical stack roles

Example:
- Required: `Java, Spring Boot, AWS`
- Candidate has `Java, AWS`
- ratio = 2/3 → pass

If candidate has only `AWS`, ratio = 1/3 → reject

### Special case
If case has only 1 required skill:
- exact match required unless role is generic PM/PMO/QA

### Role-aware skill gate
For PMO/PM/consultant cases, required skills may be non-technical:
- `進捗管理`, `顧客折衝`, `要件定義`
Need separate normalized business-skill vocabulary.

---

## Filter 5: experience / seniority gate
Only if explicitly stated.

Reject if:
- case says `5年以上必須` and candidate has `<5`
- case says `リーダー経験必須` and candidate lacks leadership tag
- case says `基本設計以降必須` and candidate has only testing

This requires structured candidate profiles. If you don’t have them reliably, don’t pretend.

---

## Filter 6: start timing
Reject if:
- case start month is fixed and candidate available date is later than acceptable window

Example:
- case `7月即日`
- candidate available `9月`
→ reject

---

## Hard filter summary: exact order
1. status/inactive
2. contract/nationality/clearance/language
3. rate
4. remote/location
5. required skill threshold
6. experience/seniority
7. start timing

Then scoring for survivors.

---

# Q4: Pipeline integration risk

## Recommendation
**c) Both (backfill + forward pipeline)**

Anything else creates split-brain data.

---

## Exact rollout plan

## Step 1: build extractors as pure functions
Do not embed parsing logic directly in `mail_pipeline.py`.

Create:
```python
extractors/rate_extractor.py
extractors/remote_extractor.py
extractors/location_extractor.py
```

Each returns:
```python
{
  "value_fields": ...,
  "method": "regex|llm",
  "confidence": ...,
  "evidence": ...
}
```

---

## Step 2: backfill existing 469 active cases
Run one-time backfill first, because:
- benchmark needs before/after comparison
- matching_v3 daily run needs corrected fields immediately
- leaving old records dirty means your filter effectiveness will look worse than it is

### Backfill order
1. rate normalization
2. remote extraction
3. location extraction
4. re-run matching on benchmark cohort
5. inspect deltas

---

## Step 3: wire into forward pipeline
At structuring time, every new email should pass through:
1. LLM structuring
2. deterministic post-processors:
   - rate extractor
   - remote extractor
   - location extractor
3. persistence to Notion

Important: **post-process after LLM**, not before. Why?
Because you may want:
- raw mail text
- LLM structured fields
- extractor overrides if higher-confidence deterministic evidence exists

### Precedence rule
```python
if regex_confidence >= llm_confidence:
    use regex result
else:
    use llm result
```

For rate and remote, I would usually trust regex more for explicit patterns.

---

## Step 4: add idempotent reparse job
Because patterns will evolve.

Create scheduled task:
```python
reparse_cases.py --since 30d --fields rate,remote,location --only-low-confidence
```

Run nightly or weekly.

This makes “ERROR retry after extraction fixes” actually workable.

---

# Q5: スキル見合い handling

## Recommendation
Use:
- `rate_type = skill_dependent_no_number` when no number exists
- `rate_type = skill_dependent_with_cap` when MAX exists
- numeric fields remain `NULL` unless explicitly extractable

Do **not** estimate a rate range.

---

## Why not estimate?
Because you’ll convert commercial ambiguity into fake precision.
That will break matching in two ways:
1. false rejection of good candidates
2. false attraction toward cases that don’t actually support the inferred budget

“スキル見合い” is not missing data in the same sense as absent rate.
It is a commercial condition.

So store it as a first-class state.

---

## Exact storage rules

### Case A: `スキル見合い`
```json
{
  "rate_min_man": null,
  "rate_max_man": null,
  "rate_type": "skill_dependent_no_number",
  "rate_confidence": 1.0
}
```

### Case B: `スキル見合い（MAX65万）`
```json
{
  "rate_min_man": null,
  "rate_max_man": 65,
  "rate_type": "skill_dependent_with_cap",
  "rate_confidence": 1.0
}
```

### Matching behavior
- `skill_dependent_no_number`: do not hard reject on rate
- `skill_dependent_with_cap`: hard reject only if candidate minimum clearly exceeds cap

### UI / Notion display
Create formula/display field:
- `65万まで(スキル見合い)`
- `スキル見合い`
instead of showing blank numeric confusion

---

# Q6: 20–30 case mini benchmark design

## Recommendation
Use **30 cases**, not 20, because you need coverage across the new pattern classes.

20 is too fragile if you want per-pattern error analysis.

---

## Benchmark purpose
This mini benchmark is not a generic quality set.
It is specifically to validate:
1. rate parsing
2. remote parsing
3. required skill extraction quality enough for hard filtering
4. downstream filter decision correctness

---

## Case selection: exact stratified sample

Pick 30 from active/representative cases.

## Rate strata
Include:
- 6 cases: explicit range (`60〜70万`)
- 4 cases: max only (`MAX70万`)
- 4 cases: `スキル見合い` only
- 4 cases: `スキル見合い + MAX`
- 4 cases: no rate present
- 2 cases: tricky ambiguous budget wording

Total rate coverage: 24  
Some cases can overlap with remote strata.

## Remote strata
Ensure among the 30:
- 5 full remote
- 5 hybrid
- 5 onsite
- 5 ambiguous `リモート`
- 5 no mention
- 5 tricky conditional wording (`初日出社`, `立ち上がり出社後リモート`, `地方不可`)

This can overlap with rate classes.

## Skill strata
Ensure:
- 10 technical backend
- 5 frontend/mobile
- 5 infra/cloud
- 5 PM/PMO/BA
- 5 QA/data/other

Goal: challenge normalization and required/preferred separation.

---

## Gold annotation fields

For each benchmark case, annotate manually:

```yaml
case_id:
raw_text:
gold:
  rate_present: bool
  rate_min_man: int|null
  rate_max_man: int|null
  rate_type: enum
  remote_type: enum
  remote_days_per_week_min: int|null
  remote_days_per_week_max: int|null
  initial_onsite_required: bool|null
  location_city_or_area: string|null
  required_skills: [normalized_skill_keys]
  preferred_skills: [normalized_skill_keys]
  required_years_experience: int|null
  start_date_category: enum["asap","yyyy-mm","flexible","unknown"]
  hard_filter_expected:
    candidate_A: pass/reject
    candidate_B: pass/reject
    candidate_C: pass/reject
```

---

## Why annotate candidate pass/reject too?
Because extractor accuracy alone is not enough.
You need to know whether the new pipeline improves **matching decisions**.

Use 3–5 representative candidate profiles against the same 30 cases.

Example candidates:
- Candidate A: Java backend, 65万 min, hybrid ok
- Candidate B: PMO, 80万 min, onsite ok
- Candidate C: React frontend, full-remote only
- Candidate D: AWS infra, 75万 min, hybrid ok

Then measure whether filter decisions match human judgment.

---

## Scoring metrics

## Field extraction metrics
For each field:

### Rate
- exact match on `rate_type`
- exact match on `rate_max_man`
- exact match on `rate_min_man`
- “recoverable from 0” success rate

### Remote
- category accuracy
- day-count extraction accuracy for hybrid
- conditional flag accuracy (`initial_onsite_required`)

### Skills
For `required_skills` and `preferred_skills` separately:
- precision
- recall
- F1

Do not use only exact-set match; too brittle.

---

## Downstream metrics
For each candidate-case pair:
- hard filter decision accuracy
- false reject count
- false pass count

This matters more than raw extraction elegance.

---

## Acceptance thresholds
Be strict.

### Rate mini benchmark targets
- numeric extraction accuracy: **>= 95%** on explicit numeric patterns
- `0 -> NULL` normalization accuracy: **100%**
- `skill_dependent` classification accuracy: **100%**

### Remote targets
- category accuracy: **>= 90%**
- full_remote / onsite precision: **>= 95%**
- hybrid day-count extraction: **>= 85%**

### Required skill targets
- required skill F1: **>= 0.85**
- preferred skill F1 can be lower for now, since it’s Phase 3

### Matching targets
- hard filter false reject rate: **< 5%**
- hard filter false pass rate: **< 10%**

If false reject is high, your thresholds are too aggressive.

---

# Concrete implementation plan for Round 2

## Week 1
### 1. Build deterministic extractors
- `rate_extractor.py`
- `remote_extractor.py`
- `location_extractor.py`

### 2. Add new Notion fields
For rate, remote, extraction method/confidence

### 3. Create benchmark YAML/CSV
30 manually labeled cases

---

## Week 2
### 4. Run backfill on 469 active cases
- fix 0万 cases
- extract remote/location
- write audit log CSV

### 5. Evaluate against benchmark
Export:
- predicted vs gold
- confusion matrix for remote categories
- rate extraction success table

---

## Week 3
### 6. Add hard filters to matching_v3
In this order:
- rate
- remote/location
- required skills
- experience/start timing if reliable

### 7. Measure reduction
Track:
- avg matches before/after
- benchmark decision accuracy
- percent cases filtered by each stage

If a filter removes almost nothing or too much, inspect it.

---

# Final devil’s advocate warnings

## 1. Biggest trap: overloading “unknown”
Do not collapse these into one:
- no rate in source
- skill-dependent
- parse failed
- remote not mentioned
- remote ambiguous

They have different matching semantics.

---

## 2. Biggest implementation mistake: letting LLM overwrite explicit regex evidence
If source says `MAX65万`, and LLM returns `70`, regex must win.

---

## 3. Biggest matching mistake: making required-skill overlap too strict too early
If your normalization is weak, hard filters will create false rejects.
Start with:
- exact normalized skill matching
- modest threshold
- benchmark-driven tuning

---

## 4. Biggest process mistake: forward-only deployment
If you don’t backfill first, your daily matching metrics will be half old logic, half new logic. You won’t know what improved.

---

If you want, in Round 3 I can give you:
1. exact regex patterns for Japanese rate/remote extraction,
2. the Notion schema changes,
3. pseudocode for `matching_v4` hard filter pipeline.