Here are the **top 3 fixes**, in priority order, that will have the **biggest impact** on production readiness.

---

## 1. Fail closed on out-of-vocabulary required skills
**Priority: P0 / must-do before production**

### Root cause
Right now, when **all required skills are OOV** (not in the 530-skill canonical dictionary), the skill filter effectively becomes **non-operative**, so everyone passes into `REVIEW`. That is the main driver of the **36–52 mass matches**.

This is the single biggest quality bug.

### What to change
Change matching logic from:

- **Current bad behavior**:  
  `if no required skills can be normalized -> do not filter on skills`

to:

- **Required new behavior**:  
  `if required skills exist but none are valid/normalized -> do not auto-match anyone`

### Recommended decision
For your Q1, the answer is:

- **Do not reject the case entirely**
- **Do reject candidate matching for that case unless another strong signal exists**
- **Do not cap at N** as the main fix
- **Do not rely on fuzzy matching in the first fix**

### Concrete rule
Introduce a **matchability gate**:

#### Case-level gating
If:
- extracted required skills count >= 1
- and normalized required technical skills count == 0

Then:
- mark case as `UNMATCHABLE_SKILL_OOV`
- return **0 candidates**
- send to dictionary/enrichment queue or human review

This immediately kills:
- UnrealEngine / Blueprint mass matches
- Informatica CDI
- IntraMart / IM-FormaDesigner
- WinActor
- Databricks / Azure運用保守
- 「課題」

### Why not cap at N?
A cap hides the bug instead of fixing it.  
You’d still be returning bad candidates, just fewer of them.

### Why not fuzzy matching first?
Fuzzy matching can help later, but as a first-line fix it will create new false positives:
- `Dynamics365` ↔ unrelated Microsoft terms
- `Blueprint` ↔ generic “design”
- `C++` tokenization issues
- Japanese product names matched loosely to wrong concepts

### Minimum implementation
Add these fields to every case:
- `extracted_skills`
- `normalized_skills`
- `oov_skills`
- `technical_skill_count`
- `matchability_status`

And enforce:

```python
if extracted_required_skills and len(normalized_technical_skills) == 0:
    return NO_MATCH, reason="ALL_REQUIRED_SKILLS_OOV"
```

### Expected impact
This should remove the majority of the **85% REVIEW noise** immediately.

---

## 2. Add a hard quality gate that excludes low-confidence / low-signal cases from candidate matching
**Priority: P0**

### Root cause
Your “13件固定パターン” strongly suggests that when extraction quality is weak, the system falls back to broad filters and the same permissive engineers always survive.

The pattern is not random. It means:

- low-confidence extraction cases still enter normal matching
- skill signal is absent or weak
- other filters are too soft
- some engineers are “match-anything” profiles

### What causes the fixed 13 engineers
Most likely one or more of these:

1. **Empty or sparse candidate skill profiles are treated as neutral instead of risky**
2. **Broad/shared skills dominate scoring**  
   e.g. Java, SQL, PMO, infrastructure, testing
3. **Location / domain / job-family constraints are too weak or not enforced**
4. **NEEDS_REVIEW cases still generate candidate lists**
5. **Default score floor is too permissive**

### What to change
For your Q2, the fix is:

### A. Do not produce normal candidate lists for low-quality cases
If extraction confidence is low, especially around `0.25 NEEDS_REVIEW`, then:

- either return **no candidates**
- or return **manual review only**, with no engineer recommendations

#### Recommended rule
If any of these is true:
- extraction confidence < 0.5
- normalized technical skills == 0
- case classified as non-IT / ambiguous
- location missing or contradictory
- job-family unclear

Then:
- `matching_enabled = false`
- `status = REVIEW_CASE_ONLY`

### B. Require at least one strong technical anchor
A candidate should not survive unless at least one of these is true:
- matched normalized required technical skill
- matched required role/category
- matched product/platform keyword with high precision
- matched mandatory location/work style constraint

If none are true, candidate is excluded.

### C. Penalize or exclude “universal survivors”
Audit the fixed 13 engineers for:
- empty skill vectors
- too many generic skills
- missing location constraints
- score inflation from non-skill features

Add a rule such as:
- candidates with **0 mapped hard skills** cannot be returned for technical cases
- candidates with only generic skills require stronger non-skill evidence

### Concrete guardrails
For technical案件, require:
- `matched_technical_skill_count >= 1`

For non-technical or ambiguous案件:
- do not run engineer matching

For location-sensitive cases:
- hard-filter by region/work mode before scoring

This directly addresses:
- Okinawa hotel情シス matching Tokyo engineers
- SNS marketing case matching engineers
- グローバル商品推進部 matching engineers
- Dynamics365 / C++ low-quality extraction cases returning the same 13 people

### Expected impact
This will eliminate the repeated fixed-candidate pattern and prevent weak cases from contaminating production output.

---

## 3. Split “skill validation” into technical normalization vs junk filtering, and expand dictionary only for high-value missing terms
**Priority: P1**

### Root cause
You currently have two separate issues mixed together:

1. **Good skills missing from dictionary**
   - C++
   - Dynamics365
   - WinActor
   - Databricks
   - UnrealEngine
   - Blueprint
   - Informatica CDI
   - intra-mart / IM-FormaDesigner

2. **Non-skills passing validation**
   - 課題
   - 能動的行動
   - 勤怠安定性
   - 運転免許
   - malformed strings like `java案件】java`

Both damage quality, but in different ways.

### What to change
For your Q3 and Q4:

## A. Yes, add missing real skills to the dictionary
But **not everything at once**. Add the high-frequency, high-impact ones first.

### First batch to add now
- C++
- Dynamics 365
- WinActor
- Databricks
- Unreal Engine
- Blueprint
- Informatica
- Informatica CDI
- intra-mart
- IM-FormaDesigner
- Azure 運用保守 should likely split into:
  - Azure
  - 運用保守

Also add robust aliases:
- `Dynamics365`, `Dynamics 365`
- `UE`, `UnrealEngine`, `Unreal Engine`
- `C＋＋`, `C++`
- `Win Actor`, `WinActor`

### B. Tighten validation with a denylist + type classifier
Do **not** let `validate_skill` approve generic nouns, traits, licenses, or malformed fragments as technical skills.

Create categories:
- `TECH_SKILL`
- `ROLE`
- `DOMAIN`
- `SOFT_TRAIT`
- `LICENSE`
- `TASK_WORD`
- `NOISE`

Only `TECH_SKILL` should drive technical matching.

### Block or ignore these examples
- 課題 → `TASK_WORD`
- 能動的行動 → `SOFT_TRAIT`
- 勤怠安定性 → `SOFT_TRAIT`
- 運転免許 → `LICENSE`
- java案件】java → `NOISE` after cleanup

### Recommended behavior
For Q4:
- **Block them from skill normalization if clearly non-technical**
- and **ignore them in matching even if extraction keeps them for audit**

That is better than only blocking in matching, because it improves downstream observability and confidence metrics.

### Minimum implementation
Introduce:
- normalization cleanup for punctuation/brackets
- denylist of generic Japanese business words
- positive allowlist for product/framework/language names
- classifier that only lets `TECH_SKILL` count as required hard skill

### Expected impact
This improves both precision and explainability, and prevents junk extraction from triggering OOV failure paths.

---

# Direct answers to your 5 questions

## 1. OOV required skills: reject, cap, or fuzzy?
**Best answer: neither cap nor fuzzy as first fix.**

Use this policy:
- if all required skills are OOV/non-technical → **return no candidates**
- mark case for review/dictionary expansion
- later add **controlled alias matching**, not open fuzzy matching

## 2. Cause of the “same 13 engineers” and fix?
**Cause:** low-confidence cases still enter matching, and broad/empty profiles survive weak filters.

**Fix:**
- no candidate generation for low-confidence / no-anchor cases
- require at least one matched technical anchor
- audit and penalize empty/broad engineer profiles
- hard-enforce location/job-family constraints

## 3. Should C++, Dynamics365, WinActor, etc. be added?
**Yes.** These are legitimate, high-value missing technical skills and should be added immediately with aliases.

## 4. Should validate_skill block non-technical “skills,” or should matching ignore them?
**Both, but prioritize blocking upstream.**
- classify them as non-technical
- exclude from hard-skill matching
- retain only as metadata if needed

## 5. Minimum viable fix for production?
If you want the absolute minimum safe production bundle, it is:

1. **Fail closed when all required skills are OOV**
2. **Do not match low-confidence / ambiguous cases**
3. **Add top missing real skills + block obvious non-skills**

That is the smallest set that meaningfully changes output quality.

---

# Recommended rollout order

## This week
1. **Fail closed on all-OOV required skills**
2. **Disable candidate recommendations for confidence < 0.5 or no normalized technical skills**
3. **Patch dictionary with top missing terms + denylist obvious junk**

## Next week
- audit fixed 13 engineers
- require at least 1 technical anchor
- add location/job-family hard filters
- add alias matching for known products

---

# Bottom line
If you only do 3 things, do these:

1. **Fail closed on all-OOV required skills**
2. **Stop matching low-confidence / low-signal cases**
3. **Expand real-skill dictionary and block non-technical extracted terms**

Those three changes will remove most mass false positives, eliminate the repeated 13-engineer pattern, and make the system plausibly production-usable.