# Classification v3: Score-based + Body Analysis
Date: 2026-06-22

## Architecture
- Subject scoring: ENGINEER_PATTERNS hit → eng+3, PROJECT_PATTERNS hit → proj+2, PRIORITY_KW → proj+1
- Body scoring: BODY_ENGINEER_STRONG hit → eng+3, BODY_PROJECT_STRONG hit → proj+3
- Decision: eng >= 3 AND eng >= proj → engineer (tie=engineer wins)
- Key discriminator: 「見合う案件」(engineer) vs 「見合う要員」(project)

## Body analysis (NEW)
- 先頭1000文字のみ使用（署名/引用汚染回避）
- BODY_ENGINEER_STRONG: 見合う案件, 要員情報, 弊社所属要員, 注力要員, 人材紹介, 弊社入社予定, 人材に案件募集
- BODY_PROJECT_STRONG: 見合う要員, 必須スキル, 案件情報, 募集人数, 増員

## Subject patterns added
- 案件希望/幅広希望 = person
- 経験あり+常駐可 = person

## Tie-break rule
eng_score == proj_score → engineer wins
Rationale: 人員の案件DB混入はビジネスリスク大（マッチング結果を汚染）

## Test result: 16/16 (100%)
- engineer-mikata body-only pattern: OK
- Astro project with 紹介 in body: OK (protected by 案件情報)
- EBA弊社プロパー+案件 in subject: OK (engineer wins tie)

## DB cleanup
- 90件 + 2件 EBA = 92件の偽projectを営業終了に変更
- 募集中: 602→544（クリーン）

## GPT壁打ち結論
- 見合う案件 vs 見合う要員 が最強の判定指標
- sender domainはsoft priorとして使用推奨（hard ruleは非推奨）
- body検出はscore制で安全に導入
