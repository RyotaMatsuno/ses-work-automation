# GPT-5.4: Apply Strategy Decision

Yes. For a production apply, I would **not apply all 5 fields uniformly**.

## Executive recommendation

**Apply now**
- **単価**: yes, with light guardrails
- **スキル**: yes, but only high-confidence / clean cases
- **最寄り駅**: yes, but only after a simple sanitation filter

**Do not apply now**
- **稼働可能日**: no, not to the main DB
- **経験年数**: no, extractor quality is too weak

And keep the core rule:

- **Fill empty only**
- **Never overwrite existing values**
- **Also skip dubious records, even if target field is empty**

---

# 1) Which fields are acceptable?

## A. 単価（万円）: **ACCEPT**
Why:
- 18 candidates only
- Confidence is strong and tight: **0.88–0.90**
- Extraction source is mostly structured: **subject bracket**
- Conflict examples show some interpretation issues, but conflicts are skipped anyway

Risk:
- Some records may represent desired range / max / min differently, but with **fill-empty-only**, this is manageable.

**Decision:** Apply.

### Suggested guardrails
- Accept only integer values in a sane range, e.g. **30–200**
- Skip if engineer name looks invalid
- Keep audit log: extracted source text, confidence, parsed value

---

## B. スキル: **ACCEPT, but filtered**
Why:
- 28 update candidates
- Average confidence **0.80**
- Many are clearly good subject-derived extractions
- Conflicts indicate extractor is often finding **more complete skill sets** than DB has

Risk:
- Dictionary-based low-confidence one-token extractions are weaker
- Some tokens are ambiguous or too coarse:
  - **SOC** is not a clean “skill” in many schemas
  - maybe role/domain rather than technology
- Some extracted names are invalid

**Decision:** Apply only a subset.

### Recommended rule
Apply only if:
- confidence **>= 0.85**, OR
- confidence **>= 0.70** AND all extracted skills are in a strict allowlist of canonical tech skills

And also:
- Exclude ambiguous/non-skill tags like **SOC** unless your DB explicitly allows operational domains
- Normalize synonyms before write:
  - Spring Boot / Spring relationship
  - Windows Server vs Windows
  - Amazon Linux implies Linux? probably keep both if schema is free-tag
- Skip invalid engineer names

### My practical recommendation
For this batch, I would:
- **Apply all subject-based 0.85 skill candidates**
- **Hold/review dictionary-based 0.70 candidates**
- Specifically **do not auto-apply SOC**
- Review these lower-confidence ones manually or in a second pass:
  - Swift? actually fine as a skill, but dictionary-only
  - COBOL
  - M365
  - VBA
  - Salesforce
  - VB.NET
  - Java/C
  - JP1
  - SOC -> reject or remap to domain

---

## C. 最寄り駅: **ACCEPT AFTER CLEANING**
Why:
- 57 candidates
- Average confidence **0.86**
- 54/57 look clean
- The errors are obvious sanitation failures, not deep semantic failures

Risk:
- You already found garbage:
  - `り駅`
  - `吉野町駅、通勤60分以内、C#/ASP.NET開発...`
  - `：行徳駅`

This means the extractor is usable, but raw outputs should not be blindly written.

**Decision:** Apply after a sanitation layer.

### Required sanitation rules
Before applying station:
1. Trim whitespace
2. Remove leading punctuation like `：`, `:`
3. If contains delimiters like `、`, `,`, `/`, `　`, take first plausible station token only
4. Require:
   - contains `駅` OR matches known station pattern
   - length in a sane range, e.g. **2–15 chars**
   - reject strings containing skill-like tokens (`C#`, `ASP.NET`, `Java`, etc.)
   - reject phrases with commute text (`通勤`, `徒歩`, `分以内`) unless a clean station can be isolated

### For the three examples
- `り駅` → reject
- `吉野町駅、通勤60分以内、C#/ASP.NET開発...` → sanitize to `吉野町駅` if your parser can reliably split at `、`
- `：行徳駅` → sanitize to `行徳駅`

If you cannot implement this sanitation now, **do not apply station yet**.

---

## D. 稼働可能日: **DO NOT APPLY TO MAIN DB**
This is the most important “no”.

Why:
- 115 candidates is large, but many are derived from relative phrases:
  - `即日` → converted to **today**
  - `7月〜` → converted to **2026-07-01**
- Those values are **time-sensitive interpretations**, not durable facts
- They become stale quickly
- Even if they were correct at email receipt time, they may be wrong now
- You already saw a year estimation error in conflict

This field is not like rate or station; it is **perishable**.

**Decision:** Do not auto-write parsed absolute dates from relative phrasing into the canonical DB field.

### Better approach
Store one of these instead:
- raw text: `即日`, `7月〜`, `8月以降`
- parsed date
- email received date / extraction date
- freshness timestamp

Then derive availability separately.

### If you absolutely must write something
Only apply when:
- source is an **explicit absolute date** in the text, not relative phrasing
- confidence >= **0.90**
- date is not obviously stale relative to message date rules

But based on your summary, I would **not apply this field in this production run**.

---

## E. 経験年数: **DO NOT APPLY**
Why:
- Only 5 update candidates
- Confidence goes as low as **0.65**
- Conflict examples reveal severe misreads:
  - 30 → 3.0
  - 3 → 11.0
- This is exactly the kind of field where small parse mistakes create major factual errors

Even though conflicts are skipped, the conflict behavior shows the extractor is not trustworthy enough yet.

**Decision:** Do not apply experience automatically.

Maybe only queue high-confidence cases for manual review, but not production write.

---

# 2) Should you filter by confidence threshold?

## Yes.
You should use **field-specific thresholds**, not one global threshold.

### Recommended thresholds

#### 単価
- **Auto-apply: >= 0.88**
- This includes essentially all current candidates

#### スキル
- **Auto-apply: >= 0.85**
- **Review only: 0.70–0.84**
- Additionally require allowed/canonical skill tags

#### 最寄り駅
- Confidence alone is not enough
- **Auto-apply: >= 0.85 + sanitation pass**
- **Review: 0.80–0.84**
- Reject sanitation failures regardless of confidence

#### 稼働可能日
- Even high confidence is not sufficient because the issue is **temporal semantics**, not extraction certainty
- So threshold does not solve the core problem
- **Do not auto-apply**

#### 経験年数
- **Do not auto-apply at any threshold for now**
- If you insist on testing: only queue **>=0.90** for manual review

---

# 3) 稼働可能日: should you apply?

## No, not to the production DB field.
Reason: these are **decaying facts inferred from relative language**.

`即日` is not equivalent to a durable date.  
`7月〜` is only meaningful relative to the original message timestamp.

If written into the DB as a fixed date, the value gains false precision and becomes misleading.

### Recommended policy
For now, choose one of these:

#### Option A: Skip entirely
Best if the DB has only one availability field and no provenance/freshness support.

#### Option B: Write to separate metadata fields
- `availability_raw_text`
- `availability_parsed_date`
- `availability_basis_date` (email received date)
- `availability_confidence`
- `availability_last_verified_at`

This is much safer.

#### Option C: Apply only explicit absolute dates
Examples:
- `2026/07/15から`
- `7/15開始可能` with year unambiguously inferred from mail date rules
But even then I’d be cautious.

**Bottom line:** For this run, **skip availability**.

---

# 4) 最寄り駅: apply all 57, or clean first?

## Clean first.
Do **not** apply raw station values directly.

You already found 3 bad outputs out of 57, which is over 5%. That is too high for blind production writes.

### Minimum viable cleaning
Implement a deterministic post-processor:
- strip leading punctuation
- split on `、`, `,`, `／`, `/`, `(`, `（`
- take first candidate
- trim
- reject too-short weird outputs
- reject strings containing non-station indicators such as:
  - programming languages
  - `通勤`
  - `開発`
  - `経験`
  - `可`
  - `分以内`

After this, apply only values that pass validation.

### Decision
- **Apply cleaned + validated station values**
- **Reject the rest**
- Do not send failed values to DB

---

# 5) Skills conflicts: should you append to existing DB skills instead of skip?

## Not automatically in this production run.
Even though it is tempting, **append is a form of overwrite/alteration** of an existing field state. It violates the spirit of your current rule unless explicitly approved as an exception.

Also, skills merging has hidden risks:
- synonym duplication
  - Spring + Spring Boot
  - Windows + Windows Server
- noisy additions from broad extraction
- adding non-skill tags
- tag taxonomy mismatch with Notion multi-select options

## Recommended position
### For now
- Keep production rule: **if skills already exist, skip**
- Do **not** append in the same auto-apply pipeline

### Next phase
Build a separate **“skills enrichment” workflow**:
- compare extracted vs existing
- normalize both sides
- produce proposed additions only
- human review or a separately approved append mode

This is worth doing, because your conflict data strongly suggests value:
- extracted often contains more skills than DB

But it should be a **separate policy**, not mixed into fill-empty-only.

---

# 6) Invalid names like “46397” and “54歳/男性”: skip?

## Yes. Skip records with clearly invalid engineer identifiers.
These are upstream entity resolution problems. Do not let them contaminate production.

### Recommended invalid-name rules
Skip auto-apply if engineer identifier:
- is only digits, e.g. `46397`
- is demographic text, e.g. `54歳/男性`, `28歳/男性`
- is placeholder-like:
  - `名前未記載`
  - `未記載`
  - `不明`
- is suspiciously non-name text from subject parsing

### Exception
If you have a **stable unique record ID** independently linking the memo to the correct DB row, then the displayed “name” being ugly is less dangerous. But from your wording, it sounds like these labels are evidence of poor parsing/identity extraction, so I would still skip them for this run unless identity is guaranteed by another key.

---

# 7) Overall production apply strategy: step-by-step

## Recommended production plan

### Phase 1: Hard rules
Apply only when all are true:
1. Target field is empty
2. Record identity is valid
3. Field passes field-specific threshold
4. Value passes field-specific validation/sanitation
5. Full audit log is stored

---

## Phase 2: Field-by-field apply policy

### Apply now

#### 単価
- Apply all 18 candidates that:
  - have valid identity
  - confidence >= 0.88
  - value in sane range
- Likely outcome: maybe skip `46397` if identity invalid

#### スキル
- Apply only:
  - confidence >= 0.85
  - source = subject preferred
  - normalized tags only
  - no ambiguous/non-skill tokens
  - valid identity
- Hold dictionary-only 0.70 cases for review
- Explicitly reject/hold `SOC`

#### 最寄り駅
- Run sanitation
- Apply only cleaned values that pass validation
- Reject raw garbage outputs
- Likely apply ~54–56 depending on cleaning success

---

### Do not apply now

#### 稼働可能日
- Skip production DB write
- Optionally store in staging/audit table only

#### 経験年数
- Skip production DB write
- Queue the 2 high-confidence cases for manual review if useful

---

## Phase 3: Suggested exact decisions on your current batch

### 単価
**Apply** except invalid identity rows.
- `46397: 50` → **skip** unless identity linkage is independently guaranteed
- Others likely okay

### スキル
**Apply subject-based 0.85 cases with valid names**
Examples likely okay:
- Y.I
- K.S八幡山
- H.U
- Y.K矢向
- K.T
- Y.A荻窪
- H.K
- R.M戸部
- S.O
- S.H
- M.S西川口
- K.O
- K・T
- R.M
- T.I
- T.D
- 28歳/男性 → **skip invalid identity**
- 54歳/男性 → **skip invalid identity**
- （名前未記載） → **skip invalid identity unless linked by stable ID**

**Hold/review dictionary 0.70**
- T.H志木 / Swift
- KT / COBOL
- I.R / M365
- Y.E / VBA
- KH / Salesforce
- SY / SOC → reject/hold
- KMN / VB.NET
- YM / Java,C
- SS / JP1

### 最寄り駅
**Apply after clean**
- `り駅` → reject
- `：行徳駅` → `行徳駅`
- `吉野町駅、通勤60分以内、C#/ASP.NET開発...` → `吉野町駅` if parser safely isolates it, else reject

### 稼働可能日
**Skip all 115** for the canonical field

### 経験年数
**Skip all 5** for auto-apply

---

# Final decisive recommendation

## Auto-apply in this run
1. **単価**
2. **スキル** only high-confidence, clean, valid-identity cases
3. **最寄り駅** only after sanitation/validation

## Do not auto-apply in this run
4. **稼働可能日**
5. **経験年数**

## Do not do yet
- **No append merge for skills** in production auto-apply
- Keep that as a separate enrichment workflow later

## Mandatory skips
- Records with clearly invalid parsed names/identifiers, unless row linkage is guaranteed by another stable key

---

If you want, I can turn this into a **concrete apply policy table** like:

- field
- auto-apply threshold
- validation rules
- skip conditions
- examples from this batch

so you can hand it directly to the implementation owner.