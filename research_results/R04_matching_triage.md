# R04: matching_v3 三層出力調査
調査日: 2026-06-18

## 結論（1行）
三層分岐の中核は `matcher.judge()`（NG→REVIEW→MATCH の順）だが、事業ルールと比べ **31語彙外必須スキルの自動パス・soft-skill all-pass 未実装・単価乖離REVIEW未実装・鮮度は22日超は丸ごと除外** があり、REVIEWに入るべき曖昧ケースが **MATCHとしてLINE通知される** リスクが残る。

## 振り分け条件一覧

### 判定フロー（優先順序）

```
matching_v3.py
  → flag_auto_updater（提案対象フラグ更新）
  → get_active_engineers（提案対象=True & 鮮度≤21日）
  → exclude_unit_price_review_targets（単価無効を候補から除外）
  → matcher.judge(case, engineer) × 全組み合わせ
       1. NG チェック（1件でも該当で即 return）
       2. REVIEW 理由を reasons に蓄積
       3. reasons あり → REVIEW（曖昧スキルのみの場合は NG）
       4. reasons なし → MATCH
  → MATCH/REVIEW のみ notifier キュー・Notion 更新
```

| 層 | 条件 | 実装状態 | ファイル:行 |
|---|---|---|---|
| **事前除外** | 提案対象フラグ=False（外国籍・地方・長期ブランク・短期連続・既往歴） | 実装済（`judge()` 外。毎朝 flag_auto_updater がフラグ更新） | `flag_auto_updater/rule_engine.py:42-67`, `matching_v3.py:92-97` |
| **事前除外** | 鮮度 >21日（情報取得日優先、なければ last_edited_time、不明は除外） | 実装済（マッチング候補から完全除外。`judge()` には到達しない） | `staleness_checker.py:33-80`, `notion_client.py:120-132`, `matcher.py:283-300` |
| **事前除外** | 単価未設定 / 0 / 負数（提案対象かつ単価無効） | 実装済（候補除外＋Notion備考に【単価REVIEW】追記可能） | `matcher.py:303-391`, `matching_v3.py:108-111` |
| **NG** | 粗利不足（案件上限−エンジニア単価 < 担当者別最低粗利：松野5万・岡本3万・他5万） | 実装済 | `matcher.py:47-54,140-156,21` |
| **NG** | 必須スキル不足（正規化後の canonical がエンジニア保有セットにない） | **部分実装** — ◯/×判定なし。31語彙外スキルは **チェック対象外（自動パス）** | `matcher.py:158-170` |
| **NG** | 並行スコア ≥5.0（オファー中=5、面談予定=2、面談調整中=1.5、結果待ち=面談日ベース0〜2.5） | 実装済（旧SPECのREVIEW扱いから変更） | `matcher.py:172-174,235-267` |
| **NG** | 曖昧スキルのみ（他REVIEW理由が一切ない） | 実装済 | `matcher.py:183-193` |
| **REVIEW** | エンジニア単価が未記入→推定使用 | 実装済（reasons に「エンジニア単価推定」） | `matcher.py:140-146,190-194` |
| **REVIEW** | 案件単価が未記入→推定使用 | 実装済（reasons に「案件単価推定」） | `matcher.py:147-151,190-194` |
| **REVIEW** | エンジニア情報が古い（`is_engineer_fresh`=False） | **実質未使用** — 22日超は事前除外のため live では到達しない。単体テストのみ REVIEW 確認 | `matcher.py:176-181`, `tests/test_matcher.py:90-101` |
| **REVIEW** | `ambiguous_skills` あり（structurer が抽出した曖昧・非技術スキル） | 実装済 | `matcher.py:183-184`, `structurer.py:28-30` |
| **REVIEW** | `extraction_confidence` < 0.3 | 実装済（SPEC記載の0.7ではなく **0.3**） | `matcher.py:186-188` |
| **REVIEW** | 並行スコア 0〜4.9（面談中・調整中等） | **未実装** — 5.0未満は理由にならず MATCH になりうる | `matcher.py:172-174` |
| **REVIEW** | 並行情報が当日以外 | **未実装** — `並行案件` の面談日はスコア計算のみ。memo フォールバックに日付概念なし | `matcher.py:235-267` |
| **REVIEW** | 単価乖離3〜5万（粗利は確保だが案件上限との差が大） | **未実装** — `optional_skill_bonus_ok` は定義のみで未使用 | `matcher.py:198-208` |
| **REVIEW** | 31語彙外必須スキル（要人手確認） | **未実装** — 旧SPECどおり REVIEW トリガーにするコードは削除済 | `matcher.py:165-170`（`normalize()` が None のスキルをスキップ） |
| **MATCH** | 上記 NG に該当せず、reasons が空 | 実装済 | `matcher.py:195` |
| **MATCH** | 必須スキル全保有（正規化ベースの集合包含のみ） | **部分実装** — 技術スキルの strict ◯/× なし | `matcher.py:158-170` |
| **MATCH** | 粗利確保 | 実装済 | `matcher.py:153-156` |
| **MATCH** | 並行OK | **過剰許容** — スコア<5 なら並行理由なしで MATCH | `matcher.py:172-174` |
| **MATCH** | 鮮度OK | 実装済（≤21日のみ候補に残る） | `staleness_checker.py:6,53` |
| **通知** | MATCH →「必須スキル: 全○」固定表示 | 実装済（実際のスキル判定結果ではなくテンプレ） | `notifier.py:107-119` |
| **通知** | REVIEW →「【要確認】」+ reasons 列挙 | 実装済 | `notifier.py:121-122`, `matching_v3.py:190-209` |

### 事業ルールとの照合サマリ

| 事業ルール | 実装 | ギャップ |
|---|---|---|
| NG: 必須スキル× | 集合包含のみ | ◯/×なし。語彙外は×扱いされず **MATCH化** |
| NG: 除外対象人材 | flag_auto_updater | `judge()` 内にはなし（事前フィルタで足りる設計） |
| NG: 並行スコア≥5.0 | NG | 一致 |
| REVIEW: 鮮度ギリギリ | 22日超=完全除外 | **REVIEW帯なし**（ギリギリも MATCH か除外の二択） |
| REVIEW: 並行当日以外 | なし | 未実装 |
| REVIEW: 単価乖離3-5万 | なし | 未実装 |
| MATCH: 全条件クリア | reasons 空のみ | 上記 REVIEW 欠落分が MATCH に漏れる |

## soft-skill分類の実装状況

| 方針（承認済み） | 実装 | 状態 |
|---|---|---|
| 技術スキル: strict判定（○/×） | `skill_judge.py` に ◯/×/△ の LLM 判定あり | **本番未配線** — `matching_v3.py` から import されず、`judge()` は alias 集合包含のみ |
| ヒューマン/ソフトスキル: all-pass（全員○） | なし | **未実装** — structurer が soft を `ambiguous_skills` に入れ、REVIEW トリガーにしている（`structurer.py:30`） |
| soft_aliases（.NET→C# 等） | `SkillNormalizer` に定義 | **無効** — `soft_aliases_enabled: false`（`skill_aliases.json:134`） |

**リスク**: PM/コミュ力/リーダー経験などは「全員○」ではなく「曖昧スキルあり→REVIEW」または「必須に入った場合は語彙外パス→MATCH」のどちらかになり、方針と逆の挙動になる。

## 業界経験の判定方法

| 項目 | 内容 |
|---|---|
| 経歴書ベース判定 | **未実装** — エンジニアDBに業界フィールドを参照するコードなし |
| structurer 側 | 「生保業界」等は `ambiguous_skills` に分類（`match_results.jsonl` 実績: 案件 `380450ff-...`） |
| matcher 側 | `ambiguous_skills` 非空 → REVIEW 理由追加のみ。業界マッチの真偽は見ない |
| 語彙外必須 | 業界名が `required_skills` に入った場合、正規化不能のため **スキルチェックをスkip→MATCH化しうる** |

## エッジケース分析

| ケース | 挙動 | リスク |
|---|---|---|
| **全スキル0件の案件**（`required_skills=[]`） | スキルチェック即パス。粗利・並行のみで MATCH 可能 | スキル要件不明案件が「必須スキル: 全○」通知される |
| **必須のみの案件** | 31語彙内なら集合包含。語彙外必須は無視 |  Terraform/SAP 等が必須でも MATCH になりうる |
| **尚可のみの案件**（`required_skills=[]`, `optional_skills` あり） | 尚可は `judge()` 未参照。必須0件扱い | 尚可要件を完全無視して MATCH |
| **単価未記入（エンジニア）** | 有効単価なら推定単価使用＋REVIEW。無効（None/0/負）なら **候補除外** | 推定で粗利OKなら REVIEW 通知（MATCH にはならない）— 妥当 |
| **単価未記入（案件）** | スキル・経験年数から案件単価推定（50〜80万）＋REVIEW | 推定が楽観的だと粗利NG、悲観的だと不当 REVIEW |
| **単価推定＋曖昧スキルなし＋confidence≥0.3** | 推定理由のみ → **REVIEW**（MATCH にならない） | 妥当 |
| **confidence 0.3〜0.69** | REVIEW にならず MATCH 可能 | SPEC(0.7)より緩く、構造化不確実案件が MATCH 化 |
| **並行スコア4.5（例: 面談予定+調整中+結果待ち）** | NG にならず、並行 REVIEW 理由もなし → **MATCH** | 事業ルール「並行REVIEW」と不一致 |
| **鮮度21日** | 候補に含まれる（fresh） | ギリギリでも MATCH 可。REVIEW 帯なし |
| **鮮度22日** | 候補から完全除外（ログのみ） | REVIEW すらされず提案対象外 |
| **曖昧スキルのみ＋必須スキル充足** | **NG**（「曖昧スキルのみ: 判定不可」） | 人手確認案件が通知されない（意図的か要確認） |

## 推奨アクション

- [ ] **P0**: `judge()` で `normalize(skill)` が None の必須スキルを **REVIEW**（または NG）に落とす — 現状の silent pass を解消
- [ ] **P0**: soft-skill / 業界経験を structurer 分類と matcher 判定で分離 — ソフトスキルは all-pass、業界は REVIEW 固定（経歴書連携は別タスク）
- [ ] **P1**: 並行スコア 0&lt;score&lt;5 を REVIEW 理由に追加（≥5 は NG のまま）
- [ ] **P1**: 単価乖離 REVIEW（粗利確保済みかつ案件上限−エンジニア単価が3〜5万）を `judge()` に追加
- [ ] **P1**: `extraction_confidence` 閾値を 0.3→0.7 に SPEC 整合（または事業ルール文書を 0.3 に更新）
- [ ] **P2**: 鮮度「ギリギリ」帯（例: 15〜21日）を REVIEW にし、22日超除外と役割分担
- [ ] **P2**: `skill_judge.py` を本番配線するか方針決定 — 配線する場合は技術=strict・ソフト=all-pass を `judge()` 前段に組み込み（未配線の現状は R05 参照）
- [ ] **P2**: `optional_skill_bonus_ok` を粗利/単価 REVIEW 判定に接続するか、尚可スキル無視を仕様として明文化
- [ ] **P2**: notifier の「必須スキル: 全○」を、実際にチェックしたスキル種別（技術のみ等）に合わせて表示修正
