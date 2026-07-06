# GPT-5.4: Commercial SES Matching Requirements

Below is a **requirements document outline for a commercially sellable SES matching engine** tailored to the **Japan SES / engineer staffing** industry.

I’m optimizing for your reality:

- small SES operator
- engineer/project data quality is uneven
- matching must be **useful in operations**, not just “AI demo”
- product must be sellable to **other SES firms**, not only for internal use

---

# SES Matching Engine Requirements Document
## Version 0.9 Draft

---

# 0. Executive summary

## Goal
Build a **commercially sellable SES matching engine** that helps SES companies match **engineers / BP engineers** to **client projects (案件)** with:

1. **high recall**: do not miss placeable candidates  
2. **acceptable precision**: do not flood users with junk matches  
3. **explainability**: every match must show clear reasons  
4. **operational usefulness**: reduce manual screening time by at least **50%**  
5. **data tolerance**: works even when source data is incomplete, but clearly signals confidence

## Core business outcome
For an SES company, matching quality is not abstract ML quality. It must increase:

- **提案数 per recruiter per day**
- **面談化率** (proposal → interview)
- **成約率** (proposal/interview → placement)
- **稼働充足速度** (time to place idle engineer)
- **案件充足率** (ability to find matching engineers for incoming projects)

## Why SES matching is different from general job matching
This must be explicit in requirements. SES matching is not standard recruiting.

### SES-specific matching constraints
A commercially useful engine must score not only skill fit but also:

- **単価 / 希望単価 / 粗利可能性**
- **勤務地 / 通勤可能範囲 / リモート可否**
- **参画可能時期**
- **稼働状況** (available / waiting / on project / future availability)
- **商流** (direct, 1st tier BP, etc.)
- **外国籍可否 / 日本語レベル** where legally and contractually relevant
- **精算幅** (140-180, fixed, etc.)
- **面談回数**
- **年齢制限・性別制限等は原則扱わない** in recommendation logic due to compliance risk
- **必須スキル / 尚可スキル / 業務経験年数**
- **業務知識** (finance, public sector, telecom, manufacturing etc.)
- **勤務形態** (常駐 / ハイブリッド / フルリモート)
- **契約条件のNG** (短期不可, 週5必須, 出張可否, 残業可否 etc.)

A general “resume-to-job” model is not enough.

---

# 1. Product scope

## 1.1 Product definition
A B2B SaaS matching engine for SES companies that ingests:

- 案件情報 (project requirements)
- 要員情報 / エンジニア情報
- free text emails, memos, skill sheets, spreadsheets

and outputs:

- ranked candidate-to-project matches
- ranked project-to-candidate matches
- reasons / blockers / confidence
- shortlist workflows for human review and proposal

## 1.2 Primary users
1. **SES owner / sales rep**
2. **coordinator / recruiter**
3. **partner management staff**
4. optionally **engineer manager**

## 1.3 Main jobs to be done
- “I received a new project email. Show me who I can propose now.”
- “An engineer becomes available next month. Show me realistic案件.”
- “I need to quickly screen 50 BP candidate sheets against 1 project.”
- “Tell me why this engineer is not suitable so I can decide manually.”

---

# 2. Commercially sellable success criteria

A product is commercially sellable only if it delivers measurable operational value within **30 days** of onboarding.

## 2.1 Buyer-facing business KPIs
Minimum target after onboarding:

- **50% reduction** in first-pass manual screening time
- **3x increase** in “reviewable shortlist generation speed”
- **top-10 shortlist recall ≥ 85%** against human-reviewed good candidates
- **proposal conversion non-inferior** to current manual process within pilot
- **data ingestion setup within 2 weeks**
- **first useful matches within 7 days**

## 2.2 Internal quality bar for sellability
Before external sale, system should achieve:

- for new project → top 10 engineer suggestions:
  - **Recall@10 ≥ 85%**
  - **Precision@10 ≥ 40%**
- for new engineer → top 10 project suggestions:
  - **Recall@10 ≥ 80%**
  - **Precision@10 ≥ 35%**

These precision numbers may look low vs consumer search, but in SES operations they are acceptable **if ranking is strong and reasons are explicit**, because human review remains in loop.

### More practical bar
For each incoming project:
- return at least **3 review-worthy candidates** in **60%+** of cases where such candidates actually exist in DB
- avoid “zero match” outcome caused by missing engineer fields when memo text contains usable info

Your current **0.18 matches/case** is far below commercial threshold.

---

# 3. Minimum data quality requirements

This is the biggest gap.

## 3.1 Non-negotiable principle
**No matching engine can be commercially sold if engineer DB quality is significantly worse than project DB quality.**

Right now project DB is usable; engineer DB is not.

The engine is currently failing mostly because:
- desired rate is **0% populated**
- location/commute is absent
- experience years mostly absent
- 35 engineers have zero skills despite memo text existing
- status may not be enforced
- hard filters likely eliminate usable candidates due to missing values

## 3.2 Minimum viable engineer data completeness targets
For production-grade matching, require the following on **active / placeable engineers only**, not total historical DB.

### Essential fields: target completeness
- **稼働状況 (availability status): 100%**
- **参画可能時期: 95%+**
- **スキル（canonicalized）: 95%+**
- **主要スキル経験年数: 80%+**
- **希望単価 or current unit rate range: 85%+**
- **勤務地 / 通勤拠点 / remote preference: 90%+**
- **雇用区分 / BP or own employee: 100%**
- **日本語レベル (if applicable): 90%+**
- **フルタイム可否 / 週5可否: 95%+**

### Strongly recommended fields
- **業界経験 (finance/public/manufacturing/etc.): 70%+**
- **工程経験 (要件定義/設計/開発/テスト/運用): 80%+**
- **資格: 40%+**
- **マネジメント経験: 60%+**
- **精算幅希望/許容: 60%+**
- **面談可能時間帯 / 面談対応可否: 80%+**

## 3.3 Essential project data completeness targets
Your project DB is relatively good, but to be sellable target:

- 必須スキル: **98%+**
- 尚可スキル: **85%+**
- 単価レンジ: **90%+**
- 勤務地: **95%+**
- リモート種別: **100%**
- 参画時期: **95%+**
- 稼働条件（週5/常駐頻度）: **90%+**
- 商流 / 国籍可否 / 面談回数 / 精算幅: **80%+**

## 3.4 Active-record-only matching requirement
Do not match against all 208 engineers equally.

Define an **active matching pool**:
- status in {提案可能, 待機中, 1か月以内空き予定, 営業中}
- updated within last **45 days**
- minimum profile quality score ≥ **70/100**

Commercial product must separate:
- **active pool**
- **inactive archive**
- **candidate pool needing enrichment**

Without this, precision collapses.

---

# 4. Data model requirements

## 4.1 Engineer schema: essential
Required normalized fields:

- engineer_id
- source_company
- employment_type (own / BP / freelancer)
- availability_status
- available_from
- desired_rate_min
- desired_rate_max
- current_rate_reference
- preferred_locations
- nearest_station or home_prefecture
- remote_preference
- commute_limit_minutes
- japanese_level
- work_style_constraints
- main_skills[]
- sub_skills[]
- skill_years per skill
- phases_experience[]
- industry_experience[]
- role_level (member / lead / PM / architect)
- years_total_experience
- memo_raw
- last_updated_at

## 4.2 Project schema: essential
- project_id
- client_type (end / SIer / BP)
- required_skills_must[]
- optional_skills[]
- min_years_by_skill
- phase_requirements[]
- industry_domain
- rate_min
- rate_max
- location
- remote_type
- on_site_days_per_week
- start_date
- duration
- nationality_policy
- japanese_level_required
- interview_count
- settlement_range
- commercial_flow
- remarks_raw
- last_updated_at

## 4.3 Match result schema
Each match must include:
- match_score (0–100)
- confidence_score (0–100)
- skill_fit_score
- commercial_fit_score
- location_fit_score
- timing_fit_score
- availability_fit
- hard-blockers[]
- review_flags[]
- explanation_text
- missing_data_impacts[]

This is essential for explainability and trust.

---

# 5. Data extraction requirements

## 5.1 Yes: engineer skill extraction from raw text should be automated
This is mandatory.

Given your current state, **automated extraction from raw text memos / skill sheets is the highest ROI improvement**.

If 35 engineers have zero skills despite text containing skills, your current matching engine is underfed.

## 5.2 Required extraction pipeline
For engineer data, build a pipeline parallel to project extraction:

**input**  
- skill sheets
- email body
- attached text/PDF/docx/xlsx
- recruiter memos
- historical proposal notes

**pipeline**
1. document parsing / OCR if needed
2. LLM extraction to structured candidate schema
3. rule normalization to canonical dictionary
4. confidence scoring per field
5. human correction UI for low-confidence fields
6. write back to structured DB

## 5.3 Extraction performance targets
Before commercial launch:

### For engineer extraction
- skill extraction field-level precision: **≥ 90%**
- skill extraction field-level recall: **≥ 85%**
- availability extraction precision: **≥ 95%**
- rate extraction precision: **≥ 95%**
- location extraction precision: **≥ 95%**
- Japanese level extraction precision: **≥ 90%**

### For project extraction
- required skill precision: **≥ 95%**
- rate precision: **≥ 95%**
- remote type precision: **≥ 98%**

## 5.4 Field confidence handling
Any extracted field should include:
- value
- confidence
- source span / source document
- extraction timestamp

If confidence < threshold:
- e.g. **<0.75**, do not use as a hard filter
- display “needs review”

This is crucial in SES where one bad parse can wrongly block a profitable proposal.

---

# 6. Matching logic requirements

## 6.1 Recommendation philosophy
For SES, the engine should be **recall-first in candidate generation, precision-second in ranking**.

Why:
- missing a placeable engineer costs direct revenue
- sales can manually reject bad ranked options
- zero results destroy trust faster than a few explainable low-ranked results

## 6.2 Recommended architecture
Use a **hybrid architecture**:

### Stage 1: broad candidate generation
Use rules + normalized search, not LLM.
Purpose: high recall, low cost, fast.

Should include:
- alias-expanded skill matching
- partial skill overlap
- related skill families
- phase match
- role level match
- timing / rate / remote compatibility
- soft handling of missing values

### Stage 2: deterministic scoring
Weighted rule-based score, fully explainable.

### Stage 3: optional LLM reranking
Use LLM only on top **20–50 candidates per query** to:
- interpret memo nuance
- evaluate transferable skills
- summarize why match is plausible
- generate recruiter-facing rationale

This is the right commercial design.  
**Do not make LLM the only matcher.**

## 6.3 Why not rule-only?
Rule-only is safe and explainable, but in SES it fails on:
- memo-only hidden skills
- nuanced transferable experience
- similar but non-identical stacks
- domain equivalence
- “must have 1 skill, nice to have 4 skills” tradeoffs

Your current low match rate is a clear warning.

## 6.4 Hard filters vs soft filters
Current engine likely uses too many hard filters.

### Hard filters should be limited to true blockers only:
- availability impossible
- rate clearly impossible beyond tolerance
- work style impossible (e.g. full on-site but engineer remote-only)
- required Japanese level not met where mandatory
- legal/contractual non-negotiables

### Soft filters should be ranked, not blocked:
- optional skills
- exact location preference
- exact industry match
- years of experience slightly below target
- phase mismatch if adjacent
- missing non-core field

## 6.5 Recommended scoring model
Total score: **100 points**

Suggested weights:

### Skill fit: 40
- must-skill coverage: 25
- optional-skill coverage: 10
- adjacent/transferable skills: 5

### Experience fit: 15
- years by key skill: 8
- phase experience: 5
- industry/domain experience: 2

### Commercial fit: 20
- rate compatibility: 10
- commercial flow / contract suitability: 5
- settlement/interview conditions: 5

### Work style fit: 15
- location/commute: 7
- remote style: 5
- weekly attendance / flexibility: 3

### Timing / availability fit: 10
- available from date: 7
- current status confidence: 3

Then assign:
- **85+**: highly recommend
- **70–84**: recommend
- **55–69**: possible / human review
- **<55**: low priority

## 6.6 Missing data policy
If a field is missing:
- do not fail closed unless it is a true blocker
- apply confidence penalty
- show “match quality limited by missing engineer rate/location/etc.”

This single requirement will improve outcomes materially.

---

# 7. Matching quality metrics

## 7.1 What to optimize in SES
The most useful ranking metrics:

- **Recall@5 / Recall@10**
- **Precision@5 / Precision@10**
- **Shortlist acceptance rate**  
  (% of suggested matches that recruiters mark as “review-worthy”)
- **Proposal rate from suggestions**
- **Interview rate from suggestions**
- **Placement rate from suggestions**

## 7.2 Recommended target metrics for commercial readiness
### Offline evaluation
- Recall@10: **≥ 85%**
- Precision@10: **≥ 40%**
- NDCG@10: **≥ 0.75**
- Zero-result rate on matchable projects: **< 15%**
- Active engineer profile low-quality exclusion rate: **100%** of profile score < threshold

### Online pilot evaluation
- recruiter acceptance rate of top-10 suggestions: **≥ 50%**
- proposal conversion from accepted suggestions: **≥ 20%**
- interview conversion from proposals: should be within **90% of manual baseline** or better
- manual screening time reduction: **≥ 50%**

## 7.3 Precision/recall tradeoff for SES
For SES, do **not** target extremely high raw precision at the cost of recall.

Better target:
- top 3 very strong
- top 10 broad enough to catch hidden opportunities

Operationally:
- top 3 precision should be **60%+**
- top 10 precision can be **35–45%**
- recall@10 should be much higher than precision priority

---

# 8. Benchmark and ground truth methodology

## 8.1 You can measure quality without “perfect ground truth”
Use **human-reviewed relevance labels** from real workflows.

Create labels:
- **A** = proposal-ready
- **B** = worth reviewing / maybe propose
- **C** = not suitable
- **X** = data insufficient to judge

For offline evaluation, treat:
- A and B as relevant for recall
- A only as strong precision target
- X excluded or analyzed separately

## 8.2 Ground truth dataset construction
Build a dataset of at least:

### Phase 1: internal validation
- **100 projects**
- **100 engineers**
- sample ~**5,000–10,000 evaluated pairs** using stratified sampling

### Phase 2: stronger benchmark
- **200 projects**
- **200 engineers**
- human-label top-ranked and random negatives
- total labeled pairs: **15,000–20,000**

## 8.3 Labeling process
Use 2 experienced SES reviewers.

For each pair, label:
- suitable? A/B/C/X
- reason codes:
  - skill gap
  - rate NG
  - location NG
  - timing NG
  - Japanese level NG
  - phase mismatch
  - domain mismatch
  - data missing
- confidence in judgment

Measure inter-rater agreement:
- Cohen’s kappa target **≥ 0.65**

## 8.4 Historical outcomes as weak ground truth
Use:
- actual proposals sent
- interviews scheduled
- placements closed
- recruiter shortlist notes

But do not rely only on history:
- historical choices are biased by incomplete awareness
- many missed matches were never proposed

So combine:
1. historical positive outcomes
2. human relabeling
3. random negative sampling

---

# 9. Functional requirements

## 9.1 Core matching use cases
### UC-1: New project intake
When a project is created/updated:
- system must return top **10–20** engineer matches within **30 seconds**
- include active-only default view
- show blockers and missing data

### UC-2: New engineer intake
When an engineer profile is created/updated:
- system returns top **10–20** projects within **30 seconds**

### UC-3: Bulk candidate screening
For one project against many candidate sheets:
- parse up to **50 candidate sheets**
- rank them
- show red flags
- output proposal shortlist

### UC-4: Human correction workflow
Users can:
- edit extracted fields
- accept/reject inferred skills
- mark “actually good match” / “bad match”
- feedback must improve future ranking

## 9.2 Explainability requirements
Every match must show:
- matched must-skills
- missing must-skills
- matched optional skills
- rate fit summary
- location/remote fit summary
- timing fit summary
- data missing warnings
- final score breakdown

Example:
- “Matched: Java (5y), Spring Boot (3y), basic design, Tokyo hybrid”
- “Gap: AWS not explicit in profile”
- “Commercial: desired 70–75万 vs project 75–85万”
- “Timing: available from 2026-07, project starts ASAP”
- “Confidence reduced because commute base missing”

This is mandatory for sales trust.

## 9.3 Feedback loop requirements
Users must be able to mark:
- good suggestion
- false positive
- hidden good match missed by system
- extracted field wrong
- blocker reason

This creates training/evaluation data and is essential for productization.

---

# 10. UI / presentation requirements

## 10.1 Result list must be operational, not academic
For each suggested match, show in 1 row:

- score
- confidence
- availability
- main skills
- skill gap count
- rate fit
- location/remote fit
- start timing fit
- status
- proposal recommendation badge

## 10.2 Required views
- project → engineers
- engineer → projects
- shortlist board
- low-quality profile queue
- extraction review queue
- feedback history

## 10.3 Filtering and sorting
Users must filter by:
- score band
- hard blocker presence
- availability window
- rate range
- remote type
- company source / BP
- confidence level

## 10.4 Export/share
Essential for SES:
- export shortlist to Excel/CSV
- copy proposal summary
- generate client-facing profile summary
- generate internal “why selected” memo

---

# 11. Real-time vs batch requirements

## 11.1 Recommended architecture
Use both:

### Batch
- nightly full recompute across all active projects/engineers
- quality checks
- extraction refresh
- dashboard metrics

### Real-time / event-driven
- on new project
- on new engineer
- on profile edit
- on status change
- on rate/location update

## 11.2 Latency targets
- event-triggered top matches: **< 30 seconds**
- UI filter/sort response: **< 2 seconds**
- nightly batch for ~100k pairs: **< 30 minutes**

At your current scale, this is very feasible.

---

# 12. Commercial product MVP feature set

## 12.1 MVP must-have
To be sellable, MVP should include:

1. **project ingestion + engineer ingestion**
2. **automated extraction from raw text**
3. **normalized skill dictionary**
4. **active-pool matching**
5. **project→engineer and engineer→project ranking**
6. **score breakdown + explanations**
7. **human correction UI**
8. **feedback logging**
9. **basic analytics dashboard**
10. **CSV/Excel import-export**

Without these, it is an internal prototype, not a product.

## 12.2 Strongly recommended for MVP+
- duplicate profile detection
- company-specific skill dictionary customization
- BP source/company tracking
- account/role permissions
- audit log of field changes
- proposal history linkage

---

# 13. Missing capabilities vs market expectations

Typical SES matching tools or adjacent staffing CRMs often have some of these. To be competitive, plan for:

## 13.1 Market-expected capabilities
- email intake automation
- skill sheet parsing
- project mail parsing
- candidate/project search
- status management
- tag management
- manual shortlist creation
- notes/history
- export for proposal

## 13.2 Differentiating capabilities
These make the product more sellable:

1. **SES-specific commercial-fit scoring**
   - not just skill fit
   - includes rate, remote, availability, settlement, interview burden

2. **high-recall active pool search**
   - prevents zero results

3. **explainable match reason**
   - transparent enough for sales to trust

4. **missing data-aware scoring**
   - “we may be missing a good match because skill sheet not parsed”

5. **feedback-to-improvement loop**
   - practical learning without heavy ML ops

6. **BP ecosystem support**
   - own employees + partner engineers + layered commercial constraints

## 13.3 Features to avoid in MVP
- full autonomous proposal sending
- opaque end-to-end LLM-only ranking
- advanced embeddings without evaluation
- complex marketplace features
- engineer self-service portal
- billing/payroll integration

Those can wait.

---

# 14. Roadmap priorities

## Phase 0: Fix data foundations immediately
Priority: highest

### Deliverables
- engineer extraction pipeline from raw text
- active/inactive separation
- profile quality score
- missing data dashboard

### Success metrics
- skills completeness from **83.2% → 95%+**
- zero-skill engineers from **35 → <5**
- desired rate completeness from **0% → 85%+**
- location/remote preference completeness from **0% → 90%+**
- active profile freshness within **45 days** for **90%+**

## Phase 1: Make matching operationally useful
Priority: highest

### Deliverables
- relax fail-closed logic for non-blocking missing fields
- active-pool ranking
- score breakdown
- top-10 shortlist UI

### Success metrics
- avg matches/case from **0.18 → 5+**
- zero-result rate reduced by **70%+**
- recruiter review time cut by **50%**

## Phase 2: Build evaluation discipline
Priority: high

### Deliverables
- labeled benchmark dataset
- offline metrics dashboard
- feedback capture in UI

### Success metrics
- Recall@10 ≥ **85%**
- Precision@10 ≥ **40%**
- inter-rater kappa ≥ **0.65**

## Phase 3: Add LLM reranking and summarization
Priority: medium-high

### Deliverables
- top-N reranker
- natural-language “why matched”
- confidence-aware narrative explanation

### Success metrics
- top-3 precision improves by **10–15 points**
- no degradation in recall

## Phase 4: Productization for external sale
Priority: medium

### Deliverables
- tenant isolation
- import templates
- customer-specific dictionaries
- admin/reporting
- onboarding wizard
- usage analytics

---

# 15. Quality gates before selling externally

Do not sell before these are met.

## 15.1 Data gates
On active engineer pool:
- skills completeness **≥ 95%**
- rate completeness **≥ 85%**
- location/remote completeness **≥ 90%**
- availability completeness **≥ 95%**
- zero-skill profiles **< 3%**

## 15.2 Matching performance gates
- Recall@10 **≥ 85%**
- Precision@10 **≥ 40%**
- zero-result rate on label-positive projects **< 15%**
- explanation coverage **100%**

## 15.3 Operational gates
- new project to shortlist in **< 30 sec**
- human correction turnaround **< 2 min/profile**
- bulk import success rate **≥ 95%**
- no major extraction regression for 30 days

---

# 16. Specific answers to your 5 questions

---

## 1. Data quality requirements

### Minimum engineer data quality for matching to work
For **active engineers**, minimum viable completeness:

- skills: **95%**
- desired rate: **85%**
- availability/start date: **95%**
- location/remote preference: **90%**
- status: **100%**
- major skill years: **80%**

Without these, SES matching will not be commercially reliable.

### Should skill extraction from raw text be automated?
**Yes, absolutely. Mandatory.**
This is the single highest-impact improvement.  
Engineer extraction should mirror project extraction.

### Essential vs nice-to-have
#### Essential
- status
- available date
- skills
- skill years
- desired rate/range
- location / remote preference
- Japanese level if relevant
- work style constraints

#### Nice-to-have
- industry experience
- certifications
- management level
- settlement preference
- interview availability
- detailed domain tags

---

## 2. Matching quality metrics

### Precision/recall targets for SES
Recommended commercial target:

- Recall@10: **85%+**
- Precision@10: **40%+**
- Precision@3: **60%+**
- zero-result rate: **< 15%** on matchable cases

### How to measure without ground truth
Use:
- expert labeling (A/B/C/X)
- historical proposals/interviews/placements
- recruiter accept/reject feedback

### Good benchmark methodology
- 100–200 real projects
- 100–200 active engineers
- 5k–20k labeled pairs
- compare current manual shortlist vs engine shortlist
- measure Recall@10, Precision@10, shortlist acceptance rate

---

## 3. Architecture gaps

### Stay rule-based or add LLM?
**Hybrid.**
- rules for candidate generation + core scoring
- LLM for extraction and top-N reranking/explanation

Do not go LLM-only.

### Real-time or batch?
**Both.**
- event-triggered real-time for operational matching
- nightly batch for full recompute and QA

### How should results be presented?
As **ranked shortlist with reason codes**, blockers, and confidence.  
Not as a black-box score only.

---

## 4. Missing capabilities for commercial product

### What competing tools have
- parsing/import
- search
- status management
- shortlist/export
- notes/history

### MVP feature set
- ingestion
- extraction
- canonical skill normalization
- matching both directions
- explainable scoring
- human correction
- feedback loop
- reporting
- export

### Roadmap priority
1. engineer data extraction + completeness
2. active-pool and missing-data-aware matching
3. benchmark/evaluation
4. LLM reranking + explanation
5. multi-tenant productization

---

## 5. Evaluation methodology

### How do we prove this works before selling?
Run a **4–6 week pilot** on your own operation first.

Measure:
- manual review time before/after
- suggestion acceptance rate
- proposal count increase
- interview rate
- placement rate
- false-negative audit (“good matches engine missed”)

### Metrics buyers care about
SES buyers care about:
- time saved
- number of proposals generated
- fewer missed placements
- faster fill / faster assignment
- trust in explanations
- easy data onboarding

### How to build ground truth
- label historical and current pairs
- use 2 recruiters
- classify A/B/C/X
- include random negatives
- track disagreement reasons
- refresh monthly with live feedback

---

# 17. Immediate action plan for your current system

Given your exact current numbers, I would do this in order:

## Next 2 weeks
1. build engineer raw-text extraction
2. populate desired rate for active engineers to **85%+**
3. populate location/remote preference to **90%+**
4. extract skills for the 35 zero-skill engineers
5. define active engineer pool
6. disable fail-closed on missing non-blocking fields

## Next 2–4 weeks
7. add profile quality score
8. add match explanation breakdown
9. create 100-project benchmark set
10. label top matches + missed matches
11. tune scoring weights for recall@10

## Next 4–8 weeks
12. add LLM reranking for top 20
13. add UI feedback loop
14. measure proposal/interview conversion
15. package onboarding/import templates for external tenants

---

If you want, I can turn this into a more formal **PRD format** with sections like:

- Objectives
- Non-goals
- User stories
- Functional requirements
- Non-functional requirements
- Data requirements
- Evaluation plan
- Launch criteria

Or I can make a **very concrete “v1 requirements table”** with columns:
**Requirement / Priority / Metric / Current state / Target / Owner**.