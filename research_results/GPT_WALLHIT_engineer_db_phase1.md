# GPT-5.4 Wallhit: Engineer DB Phase 1 SPEC Design

# SPEC.md — Phase 1: Engineer DB Quality Improvement Pipeline

## 1. Overview

### 1.1 Purpose
Engineer DB（208件）の品質を改善し、SESマッチングに使える最低限の構造化データを安定的に生成する。

Phase 1 では、既存 Notion の engineer records に対して、`人員情報原文` および `備考（LINEメモ）` の非構造テキストから以下を抽出し、**既存値を上書きせず空欄のみ補完**する。

### 1.2 Goals
- 3種類の memo/text パターンに対応した engineer 向け抽出器を作る
- 以下の項目を抽出する
  - スキル
  - 単価
  - 最寄駅 / 勤務地
  - 経験年数
  - 稼働開始可能日
  - 年齢
  - 性別
- Dry-run / shadow mode で安全に検証する
- 全件 `"稼働可能"` になっている状態を解消し、実運用可能な status 設計を入れる
- matching 対象となる **Active Pool** を定義する

### 1.3 Non-goals
- 完全自動で 100% 正確なプロフィール化
- スキルの正規化を Phase 1 で完全にやり切ること
- 過去案件との高度なスコアリング改善
- LLM 前提の抽出基盤化（Phase 1 は rule-based 中心）

---

## 2. Scope

### 2.1 Input sources
各 engineer record について、以下を抽出対象とする。

1. `人員情報原文`
2. `備考（LINEメモ）`

優先順位:
- 基本は **両方連結して解析**
- ただし memo pattern による前処理を行い、件名・本文・定型タグを分離して抽出精度を上げる

### 2.2 Supported text patterns
#### Pattern 1: Auto-import from email
例:
```text
[自動取込] 件名: 【SasaTech 人材】【7月〜65万（応相談）】【RHEL / CLUSTERPRO / JP1】...
送信元: ...
受信日: ...
```

#### Pattern 2: Auto-register from email
例:
```text
【メールから自動登録】
送信者: ...
件名: D.E｜蕨駅｜iOS開発11年／Swift・Kotlin・Java...
40歳女性。最寄駅：...
```

#### Pattern 3: LINE registration
例:
```text
[LINE登録: matsuno]
【名前】Y.S（33歳男性）
【所属】弊社正社員
【開始】7月～
【最寄】船橋競馬場駅
【単価】40万円(応相談)
【スキル】PHP, Java, SQL...
```

---

## 3. Architecture Recommendation

## 3.1 Recommendation
**Modular extractor architecture** を推奨する。  
単一巨大 extractor ではなく、以下の 3 層に分ける。

1. **Document parser**
   - テキストパターン判定
   - 件名 / 本文 / 定型ラベル部分を分解
2. **Field extractors**
   - skills / rate / station / location / years / availability / age / gender を個別抽出
3. **Merge & update layer**
   - 空欄補完のみ
   - dry-run / shadow output
   - Notion 更新

### 3.2 Why modular over single extractor
単一 extractor だと以下の問題が出る。
- パターン追加時に壊れやすい
- 項目別に改善しにくい
- dry-run 比較や抽出理由の可視化がしづらい

モジュール化の利点:
- Pattern 1/2/3 の前処理を独立改善できる
- 単価抽出だけ差し替え、スキル抽出だけ改善、が可能
- マッチング品質に直結する項目から優先改善しやすい
- 将来的に LLM fallback を項目単位で追加しやすい

---

## 4. Proposed System Design

## 4.1 Pipeline flow
```text
Notion Engineer Records
  ↓
Fetch raw fields
  ↓
Normalize source text
  ↓
Detect memo pattern
  ↓
Parse into structured segments
  - subject
  - body
  - labeled blocks
  ↓
Run field extractors
  - skills
  - rate
  - station/location
  - experience years
  - availability
  - age
  - gender
  ↓
Generate candidate patch
  ↓
Merge policy check (fill empty only)
  ↓
Dry-run report / shadow output
  ↓
Optional Notion update
```

## 4.2 Core components
### A. `engineer_text_parser.py`
役割:
- Pattern 1/2/3 判定
- 件名・本文・ラベル値の分離
- ノイズ除去（送信元、受信日など）

出力例:
```json
{
  "pattern_type": "email_auto_import",
  "subject": "【7月〜65万（応相談）】【RHEL / CLUSTERPRO / JP1】...",
  "body": "...",
  "labeled_fields": {
    "開始": "7月～",
    "最寄": "船橋競馬場駅",
    "単価": "40万円(応相談)",
    "スキル": "PHP, Java, SQL"
  },
  "full_text": "..."
}
```

### B. `engineer_field_extractors/`
- `skills_extractor.py`
- `rate_extractor_engineer.py`
- `station_location_extractor.py`
- `experience_extractor.py`
- `availability_extractor.py`
- `demographics_extractor.py`

### C. `engineer_merge_policy.py`
- 空欄のみ更新
- 既存値がある場合は候補値を shadow report に記録のみ

### D. `engineer_update_runner.py`
- `--dry-run`
- `--shadow-write`
- `--apply`
- record limit / filter support

---

## 5. Data Mapping

## 5.1 Target extracted fields
Phase 1 target fields:

| Extracted concept | Notion target field |
|---|---|
| skills | スキル系フィールド |
| rate | 単価 |
| station | 最寄駅 |
| location | 勤務地 / エリア |
| experience_years | 経験年数 |
| availability_date | 稼働開始可能日 |
| age | 年齢 |
| gender | 性別 |

### 5.2 New recommended metadata fields
Phase 1 で追加推奨:
- `抽出ステータス`：未処理 / dry-run済 / 反映済 / 要確認
- `抽出ソース`：memo / 原文 / both
- `抽出日時`
- `抽出バージョン`
- `ステータス`：新しい実運用 status
- `マッチング対象`：true/false
- `ステータス更新日`

これにより rollback と監査がしやすくなる。

---

## 6. Text Parsing Design

## 6.1 Pattern detection rules
### Pattern 1
判定条件:
- `"[自動取込]"` を含む
- `件名:` を含む

抽出:
- `件名:` 行を subject として取得
- `送信元:` `受信日:` はメタデータ扱い
- それ以外は body

### Pattern 2
判定条件:
- `"【メールから自動登録】"` を含む
- `件名:` がある

抽出:
- `件名:` 行を subject
- `送信者:` はメタ
- 2行目以降を body

### Pattern 3
判定条件:
- `"[LINE登録:"` を含む
- `【項目名】値` 形式が複数ある

抽出:
- `【名前】` `【所属】` `【開始】` `【最寄】` `【単価】` `【スキル】` などを labeled_fields 化
- 全文も body に保持

## 6.2 Fallback parsing
どの pattern にも当てはまらない場合:
- 汎用 free-text parser で subject なし本文として処理

---

## 7. Skill Extraction Strategy

## 7.1 Recommendation
**辞書 + ルール + 弱い正規化** のハイブリッド方式を推奨する。  
Phase 1 では open-ended skill space を完全列挙しない。

## 7.2 Why not closed list only
今回の取りこぼし例:
- Swift
- RHEL
- CLUSTERPRO
- OCI
- Terraform

これらは実務上重要だが、固定 regex に未登録だと全滅する。  
SES 人材情報の skill space は広く、ベンダ製品名・略語・ミドルウェア名が継続的に増えるため、**固定 whitelist のみでは破綻**する。

## 7.3 Extraction approach
### Layer 1: High-confidence labeled extraction
- `【スキル】...`
- `スキル：...`
- `技術要素：...`
- `経験：...`

ここから区切り文字で分割:
- `,`
- `、`
- `/`
- `／`
- `|`
- `・`
- 改行

### Layer 2: Subject-line extraction
件名内の `【...】` ブロックを候補として走査し、以下を抽出:
- スキル列挙ブロック
- `"Swift・Kotlin・Java"`
- `"RHEL / CLUSTERPRO / JP1"`

件名は skill-rich なので優先度高。

### Layer 3: Dictionary-assisted token detection
英数字・記号を含む技術語を抽出:
- `AWS`
- `Azure`
- `GCP`
- `OCI`
- `JP1`
- `RHEL`
- `Python`
- `TypeScript`
- `Next.js`
- `Node.js`
- `Spring Boot`
- `Terraform`

方法:
- 既存 `skill_aliases.json` を拡張
- 大文字略語・製品名・言語名を辞書化
- exact / case-insensitive / normalized match を使う

### Layer 4: Generic tech-token heuristic
辞書にないものも拾うため、以下条件の token を候補化:
- 英数字混在
- `+`, `#`, `.`, `-` を含む技術語
- カタカナ製品名
- 2回以上出現 or skill section 内出現

例:
- `Nuxt`
- `Ansible`
- `Datadog`
- `CLUSTERPRO`

### Layer 5: Post-normalization
例:
- `AWS` ← `Amazon Web Services`
- `GCP` ← `Google Cloud Platform`
- `TS` → これは誤爆しやすいので安易に正規化しない
- `JavaScript` と `JS` の統合は文脈次第

## 7.4 Storage policy
Phase 1 では以下の 2 層保存が望ましい:
- `抽出スキル_raw`
- `抽出スキル_normalized`

理由:
- 正規化ミスの rollback が容易
- 将来の matching 改善に raw が使える

## 7.5 Priority
最初に件名からの skills 取り込みを強化する。  
今回の欠損改善インパクトが最も大きい。

---

## 8. Rate Extraction Adaptation

## 8.1 Current issue
既存 rate extractor は PROJECT 文脈向けであり、ENGINEER 文脈では以下に未対応の可能性が高い。
- 件名先頭の `【7月〜65万（応相談）】`
- `【単価】40万円(応相談)`
- `65万`
- `70-75万`
- `スキル見合い`
- `応相談`
- 人材側の「希望単価」「提案単価」「単金目安」

## 8.2 Required adaptations
### A. Subject-first parsing
件名の `【...】` ブロックから単価候補を優先抽出する。

対象例:
- `【7月〜65万（応相談）】`
- `【65万前後】`
- `【70-75万】`

### B. Labeled field parsing
- `【単価】40万円(応相談)`
- `単価: 65万`
- `希望単価: 70万円`
- `単金: 60万程度`

### C. Engineer-specific semantics
PROJECT 側は予算レンジだが、ENGINEER 側は以下が混在する:
- 本人希望単価
- 商流上の提案単価
- スキル見合い
- 上振れ可能性

Phase 1 では以下を抽出:
- `rate_min`
- `rate_max`
- `rate_text_raw`
- `rate_confidence`

Notion 反映は現行の `単価` に対して代表値を入れるなら:
- 単値表記 → そのまま
- レンジ → max or representative policy を明確化
- ただし可能なら raw text も別保持

## 8.3 Extraction rules
対応パターン:
- `65万`
- `65万円`
- `65万前後`
- `65万程度`
- `60〜70万`
- `60-70万`
- `MAX65万`
- `65万（応相談）`
- `スキル見合い`

## 8.4 Merge policy
既存単価ありの場合は絶対に上書きしない。  
ただし shadow report に差異を残す。

---

## 9. Station / Location Extraction

## 9.1 Why important
119/176 memo-only records に location/station 情報が含まれる可能性があるため、改善効果が大きい。

## 9.2 Extraction order
1. `【最寄】`
2. `最寄駅：`
3. 件名内駅名
4. 本文中の勤務地/対応可能エリア
5. リモート関連文言

## 9.3 Target outputs
- `station`: 例 `蕨駅`, `大宮駅`, `船橋競馬場駅`
- `location`: 例 `東京`, `埼玉`, `千葉`, `首都圏`
- optional `work_style`: 常駐 / 併用 / フルリモート

※ work_style は要件に含まれないが、status と matching の実務上有用なので候補とする。

## 9.4 Cautions
- 「最寄駅」と「勤務可能場所」は別概念
- subject の `蕨駅` と本文の `最寄駅：大宮駅` のような不一致がありうる
- Phase 1 では **labeled field > body > subject** の優先度で採用するのが安全

---

## 10. Experience / Availability / Demographics Extraction

## 10.1 Experience years
抽出対象:
- `開発11年`
- `インフラ経験7年`
- `SE経験10年以上`
- `Java 5年`
- `総経験15年`

保存方針:
- 基本は `総経験年数`
- 技術別経験年数は Phase 1 では深追いしない

## 10.2 Availability date
抽出対象:
- `7月～`
- `7月以降稼働可`
- `即日`
- `即`
- `2026/07/01～`
- `8月参画可`

正規化:
- 可能なら `YYYY-MM` または `YYYY-MM-DD`
- 年がない場合は受信日を基準に補完
- 補完した場合は `inferred=true` を内部保持

## 10.3 Age
抽出対象:
- `40歳女性`
- `Y.S（33歳男性）`
- `35才`
- `20代後半`

Phase 1 は明示的数字を優先:
- `33歳` → 33
- `20代後半` は raw に残し、 structured age は入れない or optional

## 10.4 Gender
抽出対象:
- `男性`
- `女性`

Caution:
- gender はセンシティブ。法務・倫理観点で保持要否を確認すること
- 既存運用上必要でも、matching ロジックへの利用は慎重にする
- Phase 1 では抽出しても、スコアリング要素に使わないことを推奨

---

## 11. Merge Policy

## 11.1 Core rule
**既存値が空欄の項目のみ補完する。既存値は絶対に上書きしない。**

## 11.2 Empty definition
以下を空欄扱い:
- null
- empty string
- whitespace only

以下は空欄扱いしない:
- 既存値あり
- select/status で値セット済み
- 数値 0（ただし項目によっては別途確認）

## 11.3 If multiple candidates are found
優先順位:
1. labeled field
2. body explicit statement
3. subject
4. heuristic inference

## 11.4 Conflict handling
既存値あり + 新抽出値あり:
- DB には反映しない
- shadow report に
  - record id
  - field
  - existing value
  - extracted candidate
  - source text snippet
  を残す

---

## 12. Dry-run / Shadow Mode Design

## 12.1 Modes
### `--dry-run`
- Notion 更新なし
- 画面出力 / JSON report 出力のみ

### `--shadow-write`
- Notion の本番フィールドは更新しない
- 影フィールドまたはローカルファイルに候補値を書き出す

### `--apply`
- merge policy を通過した空欄項目のみ更新

## 12.2 Required reports
### Summary report
- 処理件数
- pattern type ごとの件数
- field ごとの抽出成功件数
- field ごとの更新対象件数
- conflict 件数
- parse error 件数

### Detailed report
各 record ごとに:
- source pattern
- extracted fields
- confidence
- update/no-update reason

## 12.3 Success criteria before apply
- 30件以上のサンプル manual review
- 単価 / スキル / 最寄駅で高精度確認
- 誤抽出率が許容範囲内
- conflicts を確認し、危険パターンを修正

---

## 13. Status Management Design

## 13.1 Current problem
全件 `"稼働可能"` は意味がなく、matching eligibility の制御に使えない。

## 13.2 Proposed status model
Phase 1 では以下の運用 status を定義する。

### Primary statuses
- `稼働可能`
- `提案中`
- `面談調整中`
- `面談中`
- `結果待ち`
- `参画決定`
- `稼働中`
- `終了予定`
- `終了`
- `保留`
- `情報古い`
- `連絡不可`
- `非公開`
- `不明`

## 13.3 Meaning
- `稼働可能`: 新規提案可能
- `提案中`: 1件以上提案中だが他提案可否は別運用
- `面談調整中` / `面談中`: 温度感高い
- `結果待ち`: 面談後
- `参画決定`: 参画開始待ち
- `稼働中`: 現在アサイン中
- `終了予定`: 終了日が近い
- `終了`: レコードとしては保持
- `保留`: 一時停止
- `情報古い`: 一定期間更新なし
- `連絡不可`: 連絡不通
- `非公開`: 営業利用対象外
- `不明`: 初期移行用

## 13.4 Phase 1 implementation approach
Phase 1 では status の完全自動化はしない。  
以下の 2 段階を推奨する。

### Step A: Default reset
現行の一律 `"稼働可能"` をそのまま信用しない。  
新フィールド `実稼働ステータス` を導入し、初期値を `不明` にする。

### Step B: Rule-assisted inference
テキストに明示記載があれば推定:
- `7月以降稼働可` → `稼働可能`
- `稼働中` / `参画中` → `稼働中`
- `即日可` → `稼働可能`
- `面談予定` → `面談調整中`
- `参画決定` → `参画決定`

ただし confidence が低い場合は `不明` のままにする。

## 13.5 Status update governance
status は抽出器だけで確定させず、営業/運用更新も必要。  
Phase 1 では:
- 抽出器は `status_candidate` を出す
- 本 status 反映は限定的にする or shadow のみ
を推奨

---

## 14. Active Pool Definition

## 14.1 Purpose
matching 対象 engineer を明確に定義する。

## 14.2 Proposed definition
以下をすべて満たすものを Active Pool とする。

### Required conditions
1. `実稼働ステータス` が以下のいずれか
   - `稼働可能`
   - `提案中`
   - `面談調整中`
   - `面談中`
   - `結果待ち`
   - `終了予定`（終了日が近く、次案件探索対象なら）
2. スキル情報が存在する
3. 単価が存在する、または提案可能判断に足る情報がある
4. 情報鮮度が閾値内
   - 例: 最終更新 90日以内
5. `非公開` / `連絡不可` ではない

## 14.3 Optional stricter definition for Phase 1 matching
商用 sellable を優先するなら、初期 matching 対象はさらに絞る。

- status = `稼働可能` or `終了予定`
- skillsあり
- rateあり
- availabilityあり
- 情報鮮度 60日以内

これを `Strict Active Pool` として別管理してもよい。

---

## 15. Risk Assessment

## 15.1 Main risks
### Risk 1: Subject-line over-extraction
件名の `【...】` を何でも skill/rate と誤認する可能性。

対策:
- ブロック分類ルールを設ける
- 金額表現・技術語表現・企業名表現を分離

### Risk 2: Skill false positives
一般語を skill と誤抽出する可能性。

対策:
- labeled section を優先
- 技術辞書 + token heuristic の confidence 分離
- raw 保存

### Risk 3: Station/location confusion
最寄駅と案件勤務地を混同する可能性。

対策:
- `最寄` / `最寄駅` ラベル最優先
- `勤務地` は location に分ける

### Risk 4: Wrong availability normalization
`7月～` の年解釈を誤る可能性。

対策:
- 受信日ベース補完
- inferred flag を持つ
- date string raw も保持

### Risk 5: Existing data inconsistency remains
空欄補完のみのため、既存誤データは直らない。

対策:
- Phase 1 は安全性優先
- conflict / suspicious report を別途出す
- Phase 2 で review 修正フロー設計

### Risk 6: Status auto-inference misuse
status を過信すると営業運用が壊れる。

対策:
- Phase 1 は `status_candidate` 中心
- 重要 status は manual confirmation 前提

### Risk 7: Sensitive attribute handling
gender/age の利用がコンプライアンス上問題になる可能性。

対策:
- 抽出はしても matching score に使わない
- 利用可否を事前確認

---

## 16. Rollback Plan

## 16.1 Principles
- 本番更新前に必ず dry-run
- 更新前 snapshot を保持
- 反映内容を record/field 単位で監査可能にする

## 16.2 Required rollback measures
1. 更新対象レコードの事前エクスポート
   - record id
   - 対象フィールドの旧値
2. update log 保存
   - 実行日時
   - extractor version
   - record id
   - field
   - old value
   - new value
3. バッチ単位 rollback script
   - 直近 run の更新だけ差し戻し可能にする

## 16.3 Safe rollout strategy
- Step 1: 10件 dry-run
- Step 2: 30件 shadow review
- Step 3: 50件 apply
- Step 4: 全件 apply

---

## 17. Suggested Implementation Phases

## 17.1 Phase 1A — Discovery / Parser foundation
最優先:
- engineer_text_parser 作成
- 3 pattern 判定と subject/body/labeled_fields 分離
- dry-run report 基盤

理由:
- すべての抽出精度の土台になるため

## 17.2 Phase 1B — High-impact extractors
次に実装:
1. skills extractor
2. rate extractor
3. station extractor

理由:
- 現在の欠損改善インパクトが最大
- matching に直結

## 17.3 Phase 1C — Secondary extractors
- experience years
- availability date
- age
- gender

理由:
- 有用だが、skills/rate/station より優先度は下

## 17.4 Phase 1D — Merge / dry-run / shadow mode
- empty-only merge
- JSON/CSV detailed report
- shadow mode

※ 実際には 1A から並行で最低限実装してよい

## 17.5 Phase 1E — Status design rollout
- `実稼働ステータス` 追加
- `status_candidate` 抽出
- Active Pool flag 算出

## 17.6 Phase 1F — Production apply
- limited apply
- accuracy review
- full apply

---

## 18. Detailed Prioritization

## 18.1 What to do first
最初にやるべき順序:

1. **Parser 作成**
2. **件名からの skill/rate 抽出**
3. **LINEラベル項目からの station/rate/skills 抽出**
4. **dry-run report**
5. **empty-only apply**
6. **status / Active Pool**

## 18.2 Why this order
今回の主要欠損は:
- skill-empty 35件
- no-rate 35件
- station/location 未抽出多数

これらは subject / labeled field を取れるようにすればすぐ改善する可能性が高い。

---

## 19. Concerns / Open Questions

## 19.1 Existing Notion schema may be insufficient
以下のような保存先が無い可能性がある:
- 最寄駅
- 抽出スキル_raw
- 抽出バージョン
- 実稼働ステータス
- status_candidate

→ 先に schema 確認が必要。

## 19.2 Empty-only policy is safe but limited
既存誤データが修正されない。  
ただし Phase 1 としては妥当。商用初期段階では安全性優先でよい。

## 19.3 Skill normalization may become bottleneck
open-ended skill space のため、辞書の保守が継続的に必要。  
Phase 1 は「漏れを減らす」ことを優先し、「完全正規化」は狙わないべき。

## 19.4 Status cannot be solved by text extraction alone
実態の status は営業運用に依存する。  
抽出器だけで truth を作るのは無理がある。  
運用フローとセットで設計すべき。

## 19.5 Date normalization ambiguity
`7月～` のような情報は年補完が必要。  
受信日基準での推定ロジックを明記しないと不整合が出る。

## 19.6 Sensitive data usage
年齢・性別は抽出しても、利用目的と保持要件を要確認。  
商用製品としては扱いに慎重であるべき。

---

## 20. Acceptance Criteria

## 20.1 Functional acceptance
- 3 memo patterns を判定・解析できる
- 以下を抽出できる:
  - skills
  - rate
  - station/location
  - experience years
  - availability date
  - age
  - gender
- 空欄のみ補完できる
- dry-run / shadow mode がある
- Active Pool を算出できる

## 20.2 Quality acceptance
目標値:
- skills-empty の 상당数を補完
- no-rate の 상당数を補完
- station/location 抽出件数を大幅改善
- 誤更新ゼロ（empty-only により）
- 30件 manual review で主要項目の精度が許容範囲

---

## 21. Recommended Deliverables

1. `SPEC.md`
2. `engineer_text_parser.py`
3. `engineer_field_extractors/*`
4. `engineer_update_runner.py`
5. `engineer_merge_policy.py`
6. `skill_aliases_engineer.json` または既存 alias 拡張
7. `dry_run_report.json`
8. `rollback_snapshot.json`

---

## 22. Final Recommendation

Phase 1 は **「pattern-aware parser + modular field extractors + safe merge」** で進めるべき。  
特に優先すべきは以下。

1. 件名解析の導入  
2. LINEラベル項目の直接抽出  
3. skill/rate/station の高精度補完  
4. status を別設計に切り出すこと  

最重要ポイントは、**status の真実性と抽出補完を分けること**、そして **空欄補完のみで安全に進めること**。  
この方針なら、Phase 1 で商用利用に必要な最低限の DB 品質改善が実現しやすい。

必要なら次に、これをそのまま Cursor に渡せる形の  
**`SPEC.md` 完成版テンプレート** と **pending_tasks 分解** まで作れます。