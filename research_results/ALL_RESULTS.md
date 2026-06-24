---
R01_matching_staleness.md
---

# R01: matching_v3 鮮度チェック調査
調査日: 2026-06-18

## 結論（1行）
人材（21日）と案件（4営業日）はおおむね実装済みだが、並行情報の「当日確認のみ→REVIEW」は未実装、人材の`最終更新日`未参照・案件の`created_time`/`登録日時`不一致・一部バイパス経路に重大ギャップあり。

## 発見事項
| # | 重大度 | 内容 | ファイル:行 |
|---|---|---|---|
| 1 | 高 | 並行情報の「当日確認分のみ→REVIEW」ロジックが存在しない。確認日フィールドの参照もなく、キーワードスコアリングのみ | `matcher.py:235-267` |
| 2 | 高 | Notionから`並行案件`をパースしていないため、本番データでは備考（LINEメモ）のキーワード解析に依存 | `notion_client.py:203-222`, `matcher.py:257-267` |
| 3 | 中 | 人材鮮度が`最終更新日`を参照しない（パースはするが`staleness_checker`未使用）。`情報取得日`・`last_edited_time`のみ | `notion_client.py:219`, `staleness_checker.py:43-74` |
| 4 | 中 | 案件取得フィルタがSPEC記載の`登録日時`ではなくNotion `created_time`を使用。手動登録日とズレる可能性 | `notion_client.py:36-48`, `notion_client.py:199` |
| 5 | 中 | `judge()`内の鮮度違反はREVIEW扱い（除外ではない）。本番は事前フィルタで除外されるが、`judge()`単体呼び出し時は古い人材がREVIEW/MATCH候補になり得る | `matcher.py:176-194`, `matching_v3.py:187-188` |
| 6 | 低 | `get_proposal_target_engineers()`は鮮度フィルタなし（`audit-unit-price`経路）。マッチング本体には未使用 | `notion_client.py:51-62`, `matcher.py:398-404` |
| 7 | 低 | `is_engineer_fresh(threshold_days=...)`の引数は無視される（`_ = threshold_days`） | `matcher.py:70-73` |
| 8 | 低 | 提案対象フラグHTTP 400時は全件取得にフォールバック（鮮度フィルタは`get_active_engineers`で適用される） | `notion_client.py:125-128` |
| 9 | 低 | `_days_since()`は鮮度判定から切り離されデッドコード化。SPEC/TASKSと実装が乖離 | `matcher.py:270-276` |
| 10 | 低 | 営業日計算`_business_days_ago()`の祝日・境界テストがない | `notion_client.py:233-240`, `tests/test_notion_client.py:21-30` |

## 詳細分析

### 人材情報の鮮度チェック

**実装概要**

- 専用モジュール `staleness_checker.py` が判定の単一ソース。
- 閾値: `STALENESS_DAYS = 21`（3週間）。
- 参照日: JST（`ZoneInfo("Asia/Tokyo")`）。
- 優先順位:
  1. `情報取得日`（date プロパティ）
  2. `_last_edited_time` / `last_edited_time`（Notionページの last_edited_time）
  3. いずれも無い → `is_fresh=False`（保守的に除外）

**日付計算**

```python
days_old = (ref - info_date).days  # カレンダー日数（営業日ではない）
is_fresh = days_old <= 21
```

- `timedelta(days=21)` 相当の比較で、21日ちょうどは fresh、22日目は stale。
- ISO文字列はJSTに変換してから日付比較。

**マッチングパイプラインでの適用**

| 経路 | 適用箇所 | 挙動 |
|---|---|---|
| 本番 `_run_live` | `notion_client.get_active_engineers()` → `filter_fresh_engineers()` | 21日超はマッチング対象から**除外** |
| dry-run（JSON engineers） | `filter_fresh_engineers()` | 同上 |
| dry-run（Notion取得） | `get_active_engineers()` | 同上 |
| `judge()` 単体 | `is_engineer_fresh()` | stale → **REVIEW**（除外ではない） |

本番フローでは事前除外が機能するため、事業ルール「マッチング対象から除外」は本線で満たされている。

**ギャップ**

- `最終更新日` は `notion_client._parse_engineer_page` でパースされるが、`staleness_checker` は参照しない。TASKS.md では `最終更新日` 参照が記載されているが実装と不一致。
- `judge()` 内では stale を REVIEW に回すのみ。フィルタをバイパスした呼び出しでは除外ではなく REVIEW 通知になり得る。

**テスト**

`tests/test_matcher.py` に以下あり（`test_staleness_checker.py` は無し）:

- 20日OK / 22日NG / 21日境界 / 日付不明NG
- `情報取得日` 優先
- `filter_fresh_engineers` の除外とログ

### 案件情報の鮮度チェック

**実装概要**

- `matching_v3.py` L105: `notion.get_new_cases(days=4)`
- `notion_client._business_days_ago(4)` で4営業日前の日付を算出:
  - 基準: `datetime.now(JST).date()`
  - 土日除外: `weekday() < 5`
  - 祝日除外: `jpholiday.is_holiday()`
- Notion API フィルタ: `created_time` の `on_or_after`（ISO日付）

**4営業日の解釈**

`_business_days_ago(4)` は「今日から遡って4営業日分」を引いた日付を返す。`on_or_after` により、その日付以降に作成された案件のみ取得 → 4営業日より古い案件は除外される。

**ギャップ**

1. **フィルタ対象の不一致**: SPEC.md は `登録日時` プロパティを条件と記載（L174）だが、実装は Notion システムの `created_time` を使用。`_parse_case_page` は `登録日時` をパースするがフィルタには未使用。
2. **取得後の再検証なし**: Python側で案件の鮮度を再チェックするロジックは無い。APIフィルタのみに依存。
3. **テスト不足**: `test_get_new_cases_builds_filter` はフィルタ構造のみ確認。祝日を挟んだ `_business_days_ago` の計算値は未テスト。

### 並行情報の鮮度チェック

**事業ルール**: 並行情報は当日確認分のみ有効。それ以外は再確認必須として REVIEW に回す。

**現状実装**

- `_calc_parallel_score()` が並行の「量」をスコア化（上限5.0超で NG）。
- データソース:
  1. `並行案件` / `parallel_items` リスト（テスト・手動投入用）
  2. フォールバック: `備考（LINEメモ）` のキーワード（オファー中/面談予定/面談調整中/結果待ち）
- `結果待ち` のみ `面談日` から経過日数でスコア調整（8日超は0点）だが、これは鮮度ではなくスコアリング。

**未実装**

- 「確認日」「最終確認日」等の当日チェックが存在しない。
- 並行データが当日でない場合に REVIEW に回す分岐が無い。
- `notion_client._parse_engineer_page` は `並行案件` を Notion から取得・パースしていない。本番では備考テキスト解析のみが実質的な並行判定。

**タイムゾーン**

- `_calc_parallel_score` の `today` デフォルトは `date.today()`（ローカルTZ依存）。人材鮮度の JST 統一と不一致。

### バイパス可能なコードパス

| コードパス | 鮮度チェック | リスク |
|---|---|---|
| `_run_live` → `get_active_engineers` → `filter_fresh_engineers` | 人材: 除外 | 低（本番標準経路） |
| `_run_live` → `get_new_cases(4)` | 案件: APIフィルタのみ | 中（登録日時ズレ時） |
| `_run_dry` + fixtures engineers | `filter_fresh_engineers` 適用 | 低 |
| `matcher.judge()` 直接呼び出し | 人材: REVIEWのみ（除外しない） | 中 |
| `matcher.load_engineers()` → `get_proposal_target_engineers()` | 人材: なし | 低（audit-unit-price専用、マッチング外） |
| 提案対象フラグ HTTP 400 フォールバック | 人材: `filter_fresh`は適用 | 低（フラグフィルタのみバイパス） |
| `is_engineer_fresh(threshold_days=N)` | 引数無視、常に21日 | 低（呼び出し側の誤用リスク） |
| `matching_v3.py` LockFile `STALE_MINUTES=30` | データ鮮度とは無関係（プロセスロック） | なし |

**挿入ポイント（未実装分）**

1. **並行当日確認**: `matcher.judge()` 内、`_calc_parallel_score()` の前後。並行データに `確認日` を追加し、JST当日でなければ `reasons.append("並行情報要再確認（当日未確認）")` → REVIEW。
2. **並行データ取得**: `notion_client._parse_engineer_page` に `並行案件`（relation または rich_text）のパース追加。
3. **人材`最終更新日`**: `staleness_checker.check()` のフォールバックチェーンに `最終更新日` を `情報取得日` と `last_edited_time` の間に挿入。
4. **案件登録日時**: `get_new_cases` のフィルタを `登録日時` プロパティベースに変更、または取得後に Python 側で `登録日時` による再フィルタ。
5. **`judge()` 整合**: stale 人材を REVIEW ではなく NG/スキップに統一するか、ドキュメントと実装の役割分担を明確化。

## 推奨アクション
- [ ] `matcher.judge()` に並行情報の当日確認チェックを追加（JST基準、未確認は REVIEW）
- [ ] `notion_client._parse_engineer_page` で `並行案件` を取得し、確認日フィールドをマッピング
- [ ] `staleness_checker.check()` に `最終更新日` フォールバックを追加（`情報取得日` → `最終更新日` → `last_edited_time`）
- [ ] `get_new_cases` のフィルタを `登録日時` プロパティに合わせるか、取得後の Python 再検証を追加
- [ ] `_business_days_ago` の祝日・週末境界テストを `tests/test_notion_client.py` に追加
- [ ] `tests/test_staleness_checker.py` を新設し、JST境界・`最終更新日` フォールバックをカバー
- [ ] `_calc_parallel_score` の `today` デフォルトを JST に統一
- [ ] `judge()` 内の stale 処理を事業ルール（除外）と整合させるか、防御的に stale 時は早期 NG を検討


---
R02_matching_exclusion.md
---

# R02: matching_v3 除外ルール調査
調査日: 2026-06-18

## 結論（1行）
6ルールのうち matching_v3 本体では「提案対象フラグ」のみ実装（不完全）で、外国籍・地方・短期・ブランク・既往歴は `flag_auto_updater` 前処理に依存しており、matching_v3 内に二重チェックがないためフラグ更新失敗・未入力・Notion 400 フォールバック時に除外漏れリスクがある。

## 除外ルール実装状況
| # | ルール | 実装状態 | チェック箇所 | テスト有無 |
|---|---|---|---|---|
| 1 | 外国籍 | 未実装（matching_v3 外） | `flag_auto_updater/rule_engine.py:47-49`（前処理）。matching_v3 内の該当コードなし | No（matching_v3）/ Yes（flag_auto_updater） |
| 2 | 地方 | 未実装（matching_v3 外） | `flag_auto_updater/rule_engine.py:51-53`（前処理）。`SPEC.md:600` は v2 精緻化予定と記載 | No（matching_v3）/ Yes（flag_auto_updater） |
| 3 | 短期連続 | 未実装（matching_v3 外） | `flag_auto_updater/rule_engine.py:61-62`（`短期連続フラグ` checkbox） | No（matching_v3）/ Yes（flag_auto_updater） |
| 4 | ブランク | 未実装（matching_v3 外） | `flag_auto_updater/rule_engine.py:55-59`（`稼働終了日` から365日超） | No（matching_v3）/ Yes（flag_auto_updater） |
| 5 | 既往歴 | 未実装（matching_v3 外） | `flag_auto_updater/rule_engine.py:64-65`（`既往歴フラグ` checkbox） | No（matching_v3）/ Yes（flag_auto_updater） |
| 6 | 提案対象フラグ | 実装済（不完全） | `notion_client.py:120-132`（Notion フィルタ）、`matcher.py:358-391`（単価REVIEW除外）、`matching_v3.py:91-111`（前処理連携） | Partial（`test_unit_price_review.py` のみ。Notion 400 フォールバックのテストなし） |

## 詳細分析

### 1. 評価フロー（全体像）

```
matching_v3.py 起動
  ├─ run_flag_updater()          ← ルール1〜5を判定し Notion「提案対象フラグ」を更新
  ├─ get_active_engineers()      ← 提案対象フラグ=True のみ取得（ルール6）
  ├─ filter_fresh_engineers()    ← 21日超を除外（別ルール・鮮度）
  ├─ exclude_unit_price_review_targets()  ← 単価無効を除外（別ルール）
  └─ judge() × 全案件            ← スキル・粗利・並行のみ。除外ルール1〜5は未チェック
```

- **ルール1〜5の評価**: `flag_auto_updater/rule_engine.py` の `judge_engineer()` で **OR 評価**（1つでも該当 → `is_target=False`、理由を `除外理由` に記録）
- **ルール6の評価**: `notion_client.get_active_engineers()` で **AND 前提**（フラグ=True のみ取得）＋ `exclude_unit_price_review_targets()` で単価無効を追加除外
- **マッチング判定 `judge()`**: 粗利・必須スキル・並行スコア・鮮度・曖昧スキルのみ。人材の絶対除外ルールは一切参照しない

### 2. ルール別詳細

#### ルール1: 外国籍
- **実装場所**: `flag_auto_updater/rule_engine.py:47-49`
- **ロジック**: `国籍` select が「日本」以外 → 除外
- **ギャップ**: `国籍` 未入力は除外しない（安全側設計）。matching_v3 は `国籍` フィールドを Notion から取得すらしていない（`notion_client._parse_engineer_page` に不在）
- **案件側 `foreign_ok`**: `structurer.py` で抽出されるが `matcher.judge()` では未使用

#### ルール2: 地方人材
- **実装場所**: `flag_auto_updater/rule_engine.py:35-39, 51-53`
- **ロジック**: `居住地` が関東7都県（東京・神奈川・埼玉・千葉・茨城・栃木・群馬）以外 → 除外
- **ギャップ**: `居住地` 未入力は除外しない。matching_v3 は `居住地` を取得・判定しない。`SPEC.md:600` に「地方人材フィルタは簡易実装（最寄り駅が空の場合スキップ）→ v2 で精緻化」とあり、matching_v3 内には未実装

#### ルール3: 短期案件連続
- **実装場所**: `flag_auto_updater/rule_engine.py:61-62`
- **ロジック**: `短期連続フラグ` checkbox = True → 除外
- **ギャップ**: 自動検出ではなく **手動フラグ依存**。matching_v3 内に短期判定ロジックなし

#### ルール4: ブランク
- **実装場所**: `flag_auto_updater/rule_engine.py:55-59`
- **ロジック**: `稼働終了日` から365日超 → `ブランク{N}日` で除外
- **ギャップ**: `稼働終了日` 未入力は「現在稼働中」とみなし除外しない。事業ルール「ブランクがある人材」と実装（365日閾値・終了日ベース）の乖離の可能性あり

#### ルール5: 既往歴
- **実装場所**: `flag_auto_updater/rule_engine.py:64-65`
- **ロジック**: `既往歴フラグ` checkbox = True → 除外
- **ギャップ**: 手動フラグ依存。matching_v3 内に既往歴チェックなし

#### ルール6: 提案対象フラグ
- **実装場所**:
  - `notion_client.py:120-132` — `get_active_engineers()` で `提案対象フラグ=True` フィルタ
  - `notion_client.py:51-62` — `get_proposal_target_engineers()` も同フィルタ
  - `matcher.py:358-391` — `_is_proposal_target()` / `exclude_unit_price_review_targets()`
  - `matching_v3.py:91-97` — `run_flag_updater()` を本番実行前に必須呼び出し（失敗時は中断）
- **重大リスク**: Notion API が 400 を返すとフィルタをスキップし **全エンジニアを取得**する（`notion_client.py:126-128`）。過去ログでもこの事象が確認済み（`ENGINEER_COUNT_20260609.txt`）
- **追加除外**: 単価未設定/0/負数の提案対象者を `exclude_unit_price_review_targets()` でマッチング候補から除外（`matcher.py:374-391`）。これは事業ルール6とは別の品質ガード

### 3. 案件側除外の確認
- **結論**: 案件種別（PMO・コンサル等）による除外ロジックは **存在しない**（事業ルール「案件側の除外ルール: なし」と一致）
- `get_new_cases()`（`notion_client.py:36-49`）は登録日時（4営業日以内）のみでフィルタ
- `judge()` は全取得案件に対して全候補エンジニアを評価。案件タイプによるスキップなし
- `foreign_ok` は構造化時に抽出されるが、マッチング判定では参照されない（案件が外国籍NGでも、フラグ=True の外国籍人材が候補に残る可能性はルール1の前処理漏れに依存）

### 4. matching_v3 内の関連する別除外（事業ルール6以外）
| 除外 | 箇所 | 備考 |
|---|---|---|
| 鮮度21日超 | `staleness_checker.py` + `filter_fresh_engineers()` | 情報取得日/last_edited_time ベース |
| 単価無効 | `exclude_unit_price_review_targets()` | 提案対象フラグ=True かつ単価異常 |
| 粗利不足 | `judge()` L153-156 | マッチング判定時 NG |
| 必須スキル不足 | `judge()` L158-170 | マッチング判定時 NG |
| 並行過多 | `judge()` L172-174 | スコア≥5.0 で NG |

### 5. テストカバレッジ

**matching_v3/tests/**
| テストファイル | カバー範囲 |
|---|---|
| `flag_auto_updater/tests/test_rule_engine.py`（matching_v3 外） | ルール1〜5 各1件 + 複合除外 |
| `test_unit_price_review.py` | 提案対象フラグ=False スキップ、単価REVIEW除外 |
| `test_matcher.py` | 鮮度フィルタ（21日境界）。除外ルール1〜5のテストなし |
| `test_notion_client.py` | 案件取得フィルタのみ。提案対象フラグフィルタ・400フォールバックのテストなし |

**欠落テスト（matching_v3）**:
- 外国籍・地方・短期・ブランク・既往歴の除外
- `get_active_engineers()` の提案対象フラグ 400 エラー時の挙動
- `run_flag_updater()` 失敗時のマッチング中断

### 6. アーキテクチャ上のリスク整理

| リスク | 深刻度 | 内容 |
|---|---|---|
| 単一障害点 | 高 | ルール1〜5が `flag_auto_updater` のみ。matching_v3 の `judge()` に二重チェックなし |
| Notion 400 フォールバック | 高 | 提案対象フラグフィルタ失敗時に全員マッチング対象になる |
| 未入力の通過 | 中 | 国籍・居住地未入力は除外されない（flag_auto_updater 設計） |
| 手動フラグ依存 | 中 | 短期連続・既往歴は checkbox の手動入力に依存 |
| ブランク定義の乖離 | 低〜中 | 365日閾値・稼働終了日ベース。事業上の「ブランク」の定義と要確認 |
| flag_updater 失敗 | 低（緩和済） | `matching_v3.py:94-97` で exit≠0 なら中断。ただし前日以前のフラグ誤設定は残る |

## 推奨アクション
- [ ] `matcher.judge()` またはエンジニア取得直後に、ルール1〜5の **defense-in-depth チェック**を追加（`flag_auto_updater.rule_engine.judge_engineer` を再利用可能）
- [ ] `notion_client.get_active_engineers()` の 400 フォールバックを廃止し、フィルタ失敗時は **処理中断**（全件取得は事故リスク大）
- [ ] `notion_client._parse_engineer_page` に `国籍`・`居住地`・`短期連続フラグ`・`既往歴フラグ`・`稼働終了日` を追加し、matching_v3 単体でも除外判定可能にする
- [ ] `matching_v3/tests/` にルール1〜6の統合テストを追加（特に Notion 400 フォールバック・flag_updater 連携）
- [ ] ブランク判定の事業定義（365日閾値・稼働終了日ベース）を CEO/松野さんと再確認し、仕様と実装の整合を取る
- [ ] 短期連続・既往歴フラグの入力運用（誰がいつ立てるか）を明文化し、未入力時の漏れを監視する


---
R03_matching_scoring.md
---

# R03: matching_v3 スコア・単価調査
調査日: 2026-06-18

## 結論（1行）
並行スコアの構造化データ経路（`並行案件`）と閾値5.0は事業ルールと一致するが、本番は備考キーワードフォールバックが主で結果待ち日数が反映されない；単価・粗利は最低5万（岡本3万）チェックのみ実装され、尚可+2万上振れ・7万目標・5万超乖離・契約先別粗利率は未配線。

## 並行スコア検証

**実装箇所:** `matcher.py` — `_calc_parallel_score()` (L235-267), `_score_result_waiting()` (L227-232), `judge()` (L172-174)

| ステータス | 事業ルール | 実装値 | 一致 |
|---|---|---|---|
| 面談調整中 | 1.5 | 1.5（`並行案件` / 備考キーワード） | ○ |
| 面談予定 | 2.0 | 2.0 | ○ |
| 結果待ち（1〜2日） | 2.5 | 2.5（`並行案件` + 面談日から日数算出） | ○ |
| 結果待ち（3〜7日） | 2.0 | 2.0（同上） | ○ |
| 結果待ち（8日以降） | 0（カウントなし） | 0.0（同上） | ○ |
| オファー中 | 5.0 | 5.0 | ○ |
| 提案のみ / 並行なし | 0 | 0.0（該当キーワードなし） | ○ |
| 合計 &lt; 5.0 → 提案OK | 提案OK | `p_score < 5.0` で通過 | ○ |
| 合計 ≥ 5.0 → 提案NG | 提案NG | `p_score >= 5.0` → `return "NG"` | ○ |

**日数判定ロジック（`並行案件` 経路）**

```python
# matcher.py L227-232
if days_waiting <= 2: return 2.5   # 1-2日
if days_waiting <= 7: return 2.0   # 3-7日
return 0.0                        # 8日以降
```

テスト `test_matcher.py` L163-184 で 2日→2.5、5日→2.0、8日→0.0 を検証済み。

**不一致・注意点**

| 項目 | 内容 |
|---|---|
| 備考フォールバック | `並行案件` が空のとき `備考（LINEメモ）` のキーワード検索にフォールバック。`結果待ち` は常に **2.0固定**（日数分岐なし） |
| 面談日なしの結果待ち | `並行案件` 経路で面談日未設定時は **1.0**（事業ルールに該当ステータスなし） |
| 本番データ経路 | `notion_client._parse_engineer_page()` は `並行案件` を読み取らない。実運用では備考フォールバックが主経路 |
| 未知ステータス | `並行案件` 内の未対応ステータスは 0 加算（暗黙的に並行なし扱い） |

## 単価・粗利検証

**実装箇所:** `matcher.py` — `calc_gross_profit()` (L47-49), `meets_profit_floor()` (L52-54), `judge()` (L140-156), `optional_skill_bonus_ok()` (L198-208)

| 事業ルール | 実装状況 | 一致 |
|---|---|---|
| 粗利 = 案件単価 − エンジニア単価 | `calc_gross_profit(case_rate, engineer_rate)` | ○ |
| 最低粗利5万円（デフォルト） | `meets_profit_floor(..., floor_man=5.0)`、未満は NG | ○ |
| 担当者別フロア（松野5万/岡本3万） | `GROSS_THRESHOLDS` + `_gross_threshold(assignee)` | ○（事業ルールの「5万」と整合。岡本3万はコード独自） |
| 平均目標粗利7万円 | 未実装（5万フロアのみ） | × |
| 必須全○ + 尚可○率50%以上 → +2万上振れ可 | `optional_skill_bonus_ok()` は定義済みだが **`judge()` から未呼び出し** | × |
| 必須全○ + 尚可○率50%未満 → 案件予算内（粗利5万確保） | 上振れロジック未配線のため区別なし | × |
| 5万超の乖離 → 提案しない | 未実装（粗利フロアのみ。上振れ上限・乖離チェックなし） | × |
| 調整余地は最大5万円まで | 未実装 | × |

**尚可スキル○率計算（`optional_skill_bonus_ok`）**

```python
# matcher.py L198-208（要約）
normalized = [normalizer.normalize(skill) for skill in optional_raw]
comparable = [skill for skill in normalized if skill]  # 正規化できたもののみ
owned = sum(1 for skill in comparable if skill in eng_skills)  # eng_skillsは未正規化
return owned / len(comparable) >= 0.5
```

| 観点 | 事業ルール | 実装 | 一致 |
|---|---|---|---|
| 分母 | 尚可スキル総数 | 正規化**成功**したスキルのみ（語彙外は分母から除外） | △ |
| 分子 | ○の数 | エンジニア保有スキルとの完全一致（`skill_judge` の ○/× 判定は未使用） | × |
| エンジニア側正規化 | — | 未実施（`SpringBoot` vs `Spring Boot` で不一致の可能性） | × |
| `judge()` への組み込み | 上振れ判定に使用 | **未配線**（`matching_v3.py` L188 も `judge()` のみ） | × |

**契約先別粗利率（TERRA 80% / FT 68% / GL 60%）**

`matching_v3/` 内に契約先別粗利率の参照は**なし**。粗利は常に `案件単価 − エンジニア単価` の差額（万円）。契約先別率は `sheets_reader.py`・`freee_invoice_v2.py` 等の請求処理側に存在し、マッチング判定とは分離されている。

**単価推定・REVIEW 除外**

| 処理 | 箇所 | 内容 |
|---|---|---|
| 案件単価 null | `_estimate_case_price()` | 経験年数・スキルキーワードから 50〜80万 を推定 |
| エンジニア単価 null（judge内） | `_estimate_engineer_price()` | 45〜75万 を推定（REVIEW理由に記録） |
| 単価無効（null/0/負） | `exclude_unit_price_review_targets()` | マッチングプールから事前除外 + Notion REVIEW 監査 |

## エッジケース

| ケース | 挙動 | 評価 |
|---|---|---|
| 必須スキル0件 | `missing` が空 → スキルチェック通過。粗利のみで判定 | 意図通り（スキル見合い案件） |
| エンジニアスキル0件 | 必須スキルあり → NG「必須スキル不足」 | ○ |
| 単価未記入（null/0/負） | `matching_v3.py` 実行前にプール除外。`judge()` には到達しない | ○（ただし推定経路は別途存在） |
| 案件単価未記入 | `_estimate_case_price()` で推定。推定粗利がフロア未満なら NG、通過時は REVIEW 寄せの可能性 | △（推定誤差リスク） |
| 並行情報なし | スコア 0.0 → 並行起因の NG なし | ○ |
| 備考に複数ステータス | キーワードを**加算**（例: 面談調整中+面談予定 = 3.5） | △（構造化データと挙動差） |
| 並行スコアちょうど5.0 | `>= 5.0` で NG | ○（事業ルール「5.0以上」に一致） |
| `extraction_confidence < 0.3` | REVIEW（NG ではない） | 仕様どおり |

## 推奨アクション

- [ ] `notion_client._parse_engineer_page()` に `並行案件`（または reply_parser 連携）を追加し、備考キーワードフォールバック依存を減らす
- [ ] 備考フォールバックの `結果待ち` に日数分岐を適用するか、フォールバック廃止を検討
- [ ] `judge()` に `optional_skill_bonus_ok()` を組み込み、尚可50%以上時は `case_max + 2` まで許容・粗利7万目標を反映
- [ ] 尚可○率の分母を `optional_skills` 総数に統一し、エンジニアスキルも `SkillNormalizer` で正規化してから照合
- [ ] エンジニア単価が案件予算+5万を超える場合の NG ルール（5万超乖離）を `judge()` に追加
- [ ] 契約先別粗利率がマッチングに不要であることを SPEC に明記するか、必要ならエンジニアの契約先フィールド連携を設計
- [ ] `optional_skill_bonus_ok` のユニットテスト追加（現状 `judge()` テストのみで関数単体テストなし）


---
R04_matching_triage.md
---

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


---
R05_matching_llm_error.md
---

# R05: matching_v3 LLM・エラー処理調査
調査日: 2026-06-18

## 結論（1行）
本番フローで実際に動く LLM は `structurer.py` の案件メール JSON 構造化のみ（CostGuard 二重チェック済み）だが、`max_tokens=2000`・API リトライ/サーキットブレーカーなし・入力マスキングなし・フォールバック時の型検証不足が残存し、`skill_judge.py` は未配線のまま別モデル（Haiku）・別 CostGuard（v2）を持つ。

## LLM呼び出し一覧
| # | ファイル:行 | モデル | CostGuard | max_tokens | マスキング指示 |
|---|---|---|---|---|---|
| 1 | structurer.py:134 (`_call_openai`) | デフォルト `gpt-4.1-nano`（`cost_guard.get_model()` 経由。月次 $5 超で `FALLBACK_MODEL` / `gemini-2.0-flash` に降格） | **あり** — `matching_v3/cost_guard.CostGuard.can_call()` + `common.ledger.can_spend()` の二重チェック、`record_cost()` / `ledger.record()` で記録 | **2000**（8000 未満 ⚠️） | **なし** — 案件メール本文をそのまま LLM に送信。プロンプトに企業名・担当者・連絡先削除指示なし |
| 2 | structurer.py:114 (`_call_anthropic`) | 上記と同じ（非 gpt/o 系モデル選択時のフォールバック経路） | 同上 | **2000**（8000 未満 ⚠️） | 同上 |
| 3 | skill_judge.py:115 (`_do_api_call`) | デフォルト `claude-haiku-4-5-20251001`（`MATCH_MODEL` / `common/model_config.py`）— **gpt-4.1-nano ではない** | **あり** — 親ディレクトリ `ses_work/cost_guard.py` の `allowed()` / `finalize()`（v2）。`sys.path` に `ses_work` を insert して解決（`matching_v3/cost_guard.py` とは別モジュール） | **8000** ✓ | **なし** — スキル名リストのみ。固有名詞マスキング指示なし |
| — | notifier.py | LLM 呼び出しなし（テンプレート文字列で LINE 通知生成） | — | — | 部分対応 — エンジニア名はイニシャルのみ。案件名・担当者名（users.yaml キー）・生単価・粗利はそのまま表示（5 万抜き単価表記なし） |
| — | matcher.py | LLM 呼び出しなし（Python ルールベース判定） | — | — | — |

**補足（配線状況）**
- `matching_v3.py` → `structurer.structure()` のみ LLM 呼び出し。`skill_judge.judge_skills()` は **どのモジュールからも import されておらず本番未使用**。
- SPEC.md 設計思想どおり「LLM は JSON 構造化のみ」。調査指示の「メール文面生成」に相当する LLM 呼び出しは matching_v3 内に存在しない（LINE 通知は `notifier.py` の固定テンプレート）。
- **CostGuard 二重実装**: `matching_v3/cost_guard.py`（v1 クラス）と `ses_work/cost_guard.py`（v2 `allowed`/`finalize`）が同名で共存。本番 structurer は v1、skill_judge は v2 を使用。
- **SPEC.md との乖離**: SPEC §8 は `DAILY_COST_LIMIT_USD=6.00` / 月次 $120/$140 と記載するが、実装（`matching_v3/cost_guard.py`）は **$1.00/日・$5/$6 月次**（TASKS.md E2 の意図的変更）。

## エラーハンドリング評価
| 障害パターン | 処理 | 評価 |
|---|---|---|
| API タイムアウト | structurer: OpenAI/Anthropic クライアントに明示 `timeout` なし。例外は `matching_v3.py:177` で catch → case `ERROR`、リトライなし、**次案件へ継続** | **要改善** |
| API 利用上限（400 quota exceeded） | 2026-06-05 ログで **1,514 件**連続 `Structurer error`（Anthropic quota）。CostGuard は通過するため案件ごとに API を叩き続ける | **重大** — サーキットブレーカーなし |
| レート制限（429） | structurer: 処理なし。skill_judge: `RateLimitError` は `error_kind=transient` に分類するが **リトライ対象外**（529/overloaded のみ最大 5 回リトライ） | **要改善** |
| JSONDecodeError | structurer: fence 除去 → `json.loads` → 正規表現で `{...}` 抽出 → 失敗時 `extraction_confidence=0.0` の空スキーマ fallback（`structurer.py:164-214`） | **部分対応** — クラッシュは防ぐがサイレント劣化 |
| 空レスポンス | structurer: warning ログ後 fallback（`extraction_confidence=0.0`） | **部分対応** |
| max_tokens 切り詰め | structurer: `finish_reason=="length"` 時 warning のみ（`structurer.py:144-145`）。切り詰め JSON をそのまま parse 試行 | **要改善** — v2 既知バグ（8000 必要）の再発リスク |
| CostGuard 上限到達 | structurer 呼び出し前: `can_call()` false → `RuntimeError` → case `ERROR`。ループ前チェック（`matching_v3.py:167`）で **処理停止** | **良好** |
| skill_judge API 過負荷（529） | 指数バックオフ付き最大 5 回リトライ（`skill_judge.py:111-134`） | **良好**（ただし未配線） |
| レスポンス型・フィールド検証 | structurer: `isinstance(data, dict)` のみ。スキル配列の型・price 数値型チェックなし。skill_judge: `result` が ◯/×/△ 以外は × に正規化（`skill_judge.py:81-91`） | structurer **要改善** / skill_judge **良好** |

## コスト見積もり

### 1 回のマッチング実行あたり
| 処理 | LLM 呼び出し回数 | 備考 |
|---|---|---|
| 案件構造化（structurer） | **未処理案件 1 件につき 1 回** | `processed_db.is_processed()` でスキップ済み案件は 0 回 |
| エンジニアマッチング（matcher） | 0 回 | ルールベース |
| LINE 通知（notifier） | 0 回 | テンプレート |
| スキル LLM 判定（skill_judge） | 0 回（現状未配線） | 配線時は案件×スキルセットごとに 1 回の可能性 |

**典型 1 案件のトークン見積もり（structurer）**
- 入力: `len(prompt) // 4 + 200`（Few-shot 2 例 + 本文最大 3000 字）≈ 1,100〜3,500 tokens
- 出力見積もり: 300 tokens（phase0 実測 `phase0_cost_log.jsonl`: 出力 150〜452 tokens、コスト $0.00017〜0.00043/回）
- モデル `gpt-4.1-nano` 単価（`cost_guard.py`）: input $0.10/1M, output $0.40/1M
- **1 呼び出しあたり概算 $0.0002〜0.0004**

### 1 日の最大呼び出し回数
| 制限レイヤー | 上限（実装値） | 効果 |
|---|---|---|
| `matching_v3/cost_guard.py` | `DAILY_CALL_LIMIT=1500`, `DAILY_COST_LIMIT_USD=1.00` | script=matching_v3 の日次制限 |
| `common/ledger.py` | `COST_GUARD_DAILY_USD=8.0`（デフォルト） | 全 ses_work 横断の日次上限 |
| `ses_work/cost_guard.py` | `HARD_DAILY_LIMIT=20.0` | 緊急停止ライン（LLM_KILL 発動） |
| 稼働日 | 平日のみ（土日祝スキップ） | 1 日 1 回タスク想定 |
| 案件ソース | `get_new_cases(days=4)` | 4 営業日分の新規案件が対象だが processed_db で重複排除 |

**実運用上の上限**: 新規未処理案件数（通常数十件/日程度）と `DAILY_COST_LIMIT_USD=1.00` の早い方。$1 上限 ≈ 2,500〜5,000 件/日（nano 単価換算）だが、call limit 1500 が実質キャップ。**skill_judge 配線時は案件×エンジニア評価で呼び出しが爆増するため CostGuard v2 統合が必須。**

## 推奨アクション
- [ ] **P0**: `structurer.py` の `max_tokens` を OpenAI/Anthropic 両方 **8000 以上**に引き上げ（v2 JSONDecodeError 再発防止）
- [ ] **P0**: structurer に **429/529/timeout の指数バックオフリトライ**（skill_judge と同等）を追加
- [ ] **P0**: API 恒久エラー（400 quota / 401 auth）検知時に **サーキットブレーカー**でループ停止（6/5 の 1,514 連続失敗再発防止）
- [ ] **P0**: 案件メールを LLM 送信前に **企業名・担当者名・メール/電話をマスク**する前処理、またはプロンプトに削除指示を追加（守秘義務）
- [ ] **P1**: `notifier._build_msg` の単価表示を **粗利 5 万抜きの提示単価**に変更し、案件名の機密度もレビュー
- [ ] **P1**: structurer レスポンスに **スキーマバリデーション**（必須キー存在・配列型・price 数値型）を追加し、fallback 時は case を `REVIEW`/`ERROR` に明示分岐
- [ ] **P1**: `CostGuard.get_model()` の月次降格で `gemini-2.0-flash` に切り替わる経路を文書化し、`ledger.can_spend()` のモデル引数と **実際に呼ぶモデルを一致**させる
- [ ] **P2**: `skill_judge.py` を **本番配線するか削除するか**を決定。配線する場合は matcher から呼び出し、モデルを `gpt-4.1-nano` 方針に合わせるか CostGuard v2 予算を別枠設計
- [ ] **P2**: `matching_v3/cost_guard.py`（v1）と `ses_work/cost_guard.py`（v2）の **二重実装を統合**し、SPEC.md のコスト上限記載を実装値と同期
- [ ] **P2**: matching_v3 ローカル CostGuard（$1/日）と global ledger（$8/日）の **二重制限の意図**を SPEC に明記し、$50/日暴走再発時の防御深度を検証


---
R06_pipeline_sqlite.md
---

# R06: mail_pipeline SQLite基盤調査
調査日: 2026-06-18

## 結論（1行）
`raw_inbox.py` の UNIQUE 制約と移行ロジックは基本機能として成立しているが、**WAL / busy_timeout 未設定・プロセス間排他なし・insert の SELECT→INSERT 競合** により、30分スケジューラと手動実行の衝突時に `database is locked` や二重 LLM 処理のリスクが残る（年6000件規模の性能問題は当面なし）。

## テーブル定義分析

### raw_emails（`raw_inbox.py:18-33`）

| カラム | 型 | 制約 | 備考 |
|---|---|---|---|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | — |
| message_id | TEXT | **UNIQUE** | NOT NULL **なし**（空文字は `insert_raw_email` 側で早期 return） |
| account, received_at, sender, subject, body_text, body_hash, attachment_names, classify_result | TEXT | 制約なし | NULL 許容 |
| has_attachment | INTEGER | DEFAULT 0 | — |
| processed | INTEGER | DEFAULT 0 | 0=未処理, 1=処理済み |
| created_at | TEXT | DEFAULT datetime('now') | — |

**インデックス**
- `message_id UNIQUE` により SQLite が自動的にユニークインデックスを生成（明示 `CREATE INDEX` なし）
- `processed` / `received_at` への追加インデックスなし（現行件数では問題にならないが、`load_processed_ids()` の `WHERE processed = 1` 全件読み込みは件数比例）

**monthly_stats（VIEW, `raw_inbox.py:35-41`）**
- `strftime('%Y-%m', received_at)` × `classify_result` で GROUP BY
- `received_at` が NULL/空の行は `month = NULL` バケットに集約される

**WAL / PRAGMA 設定**
- `get_connection()`（`raw_inbox.py:49-53`）は `sqlite3.connect(path)` のみ。**journal_mode=WAL・busy_timeout・foreign_keys 等の PRAGMA 設定なし**
- デフォルト journal_mode は **DELETE**（Python sqlite3 / SQLite 標準）
- Python 3.12 の `sqlite3.connect` デフォルト `timeout=5.0` 秒がロック待ちに適用されるが、`raw_inbox.py` では明示していない

**本番 DB 状態（ファイルシステムのみ確認、`raw_inbox.db` は未オープン）**
- `processed_ids.json` は存在せず、`processed_ids.json.bak`（約 82KB）のみ → 移行完了済みと推定

## 移行ロジック分析

### 呼び出し経路（`mail_pipeline.py:336-346`）

```python
def ensure_raw_inbox_ready() -> None:
    init_raw_inbox_db(RAW_INBOX_DB)
    if PROCESSED_IDS_PATH.exists():  # processed_ids.json の存在のみ判定
        try:
            migrated = migrate_processed_ids_json(...)
        except Exception as e:
            log(f"processed_ids移行エラー: {e}")  # 失敗してもパイプラインは継続
```

### migrate_processed_ids_json（`raw_inbox.py:217-267`）の挙動

| 観点 | 実装 | 評価 |
|---|---|---|
| 移行トリガー | `processed_ids.json` が存在するときのみ | `.bak` 存在はスキップ条件に**含まれない**（json が無ければ何もしない） |
| DB 書き込み | 全 ID をループ後 **1 回 `commit()`** | クラッシュ時: commit 前なら DB 変更なし・json 温存 → **再実行可能** |
| 既存行 | `processed=0` なら UPDATE、`processed=1` ならスキップ | 冪等 |
| 新規行 | `INSERT (message_id, processed=1, classify_result='migrated')` のみ（本文なし） | 移行専用の「ゴースト行」が生成される |
| .bak リネーム | **`commit()` 成功後**に `bak.unlink()` → `shutil.move(json→bak)` | 順序は妥当（DB 確定後にソース退避） |
| 例外時 | `finally: conn.close()` のみ。**rollback 明示なし**（未 commit なら自動破棄） | 許容範囲 |
| commit 後・move 前クラッシュ | json 残存 → 次回再移行（冪等） | 復旧可能 |
| move 成功後 | json 消滅・bak 残存 | 本番はこの状態（bak のみ存在） |

**部分移行からの復旧手段**
1. **自動**: json が残っていれば次回 `ensure_raw_inbox_ready()` で再実行（UPDATE/INSERT は冪等）
2. **手動**: json が消えたが DB に不足がある場合 → `processed_ids.json.bak` から json を復元して再実行可能
3. **移行失敗が続く場合**: 例外はログのみでパイプライン継続。`load_processed_ids()` は DB の `processed=1` のみ参照するため、**移行未完了＋json 残存時は古い json の ID が DB に反映されず、同一メールの再 LLM 処理が発生しうる**

**テストカバレッジ**
- `tests/test_raw_inbox.py::test_migrate_processed_ids_json`: 1535 件移行・json 削除・bak 生成を検証
- クラッシュ中間状態・並行移行のテストなし

## 同時実行安全性

### 実行モデル
- `SPEC.md` / `TASKS.md`: Windows タスクスケジューラで **30分おき** `run_pipeline.bat` 実行
- `run_pipeline.bat`: **排他ロック・PID ファイル・mutex なし**。手動 `python mail_pipeline.py` と衝突可能
- 1 プロセス内はシングルスレッドだが、**複数プロセスが同一 `raw_inbox.db` を同時オープン**しうる

### INSERT 時の重複処理

| 関数 | 方式 | 同時実行時 |
|---|---|---|
| `insert_raw_email` | SELECT → INSERT or UPDATE（`raw_inbox.py:98-150`） | **TOCTOU 競合**: 2 プロセスが同時に SELECT 空→両方 INSERT → 片方が `IntegrityError`（未 catch → `_save_all_emails_to_raw_inbox` で log のみ） |
| `mark_processed` | `INSERT ... ON CONFLICT DO UPDATE`（`raw_inbox.py:179-186`） | **アトミック** ✓ |
| `update_classify_result` | 同上 ON CONFLICT | **アトミック** ✓ |

**processed フラグのライフサイクル**
- 初期値: `DEFAULT 0`（新規 INSERT 時）
- 更新: `save_processed_id()` → `mark_processed()`（各メール処理完了時、`mail_pipeline.py:328-333, 1612+`）
- 起動時: `load_processed_ids()` で **全 `processed=1` をメモリ set にロード**（`raw_inbox.py:157-166`）
- **問題**: 2 プロセスが同時起動すると、両方が同じ未処理 ID を「新規」と判定し、**LLM 二重実行・Notion 二重登録の可能性**（SQLite だけでは防げない）

### ロック関連

| 設定 | 現状 | 影響 |
|---|---|---|
| journal_mode | DELETE（デフォルト） | 書込中は読取もブロックされやすい |
| WAL | **未設定** | 読み書き並行性能が劣る |
| busy_timeout | Python デフォルト 5 秒（暗黙） | 長時間 LLM 処理中に別プロセスが DB 書込 → 5 秒待ち後 `OperationalError: database is locked` |
| 接続寿命 | 操作ごとに open → commit → close | 長時間トランザクションは無い（ロック保持時間は短い） |

**衝突シナリオ（30分スケジューラ × 手動実行）**
1. プロセス A が LLM 処理中（DB は都度 close）
2. プロセス B が起動 → `load_processed_ids` / `insert_raw_email` / `mark_processed` で DB アクセス
3. タイミング次第で **(a) locked エラーで raw_inbox 保存失敗**（log のみ、メール取りこぼしリスク）または **(b) 同一 msg_id の二重 LLM 処理**

`pipeline.log` 内に `database is locked` / `raw_inbox` 関連ログは未検出（2026-06-18 時点）だが、コード上の構造リスクは残存。

## 将来スケーラビリティ

**想定データ量**: 月 500 件 × 12 ヶ月 = **年 6,000 件以上**（調査指示どおり）

| 観点 | 見通し |
|---|---|
| 行数 6,000〜数万 | SQLite は問題なし（単一テーブル百万行規模まで実用） |
| 行サイズ | `body_text` 全文保存 → 1 行 5〜50KB 想定、年間 **数十〜300MB** 程度 |
| クエリ性能 | `message_id` UNIQUE 索引で point lookup は O(log n)。`load_processed_ids` の全件 scan は 6,000 件で数 ms〜数十 ms |
| monthly_stats VIEW | 6,000 行 GROUP BY は瞬時。10 万行超で初めて体感 |
| VACUUM | 通常 INSERT のみなら **不要**。大量 DELETE アーカイブ時のみ検討 |
| init_db 毎操作 | 各関数が `init_db()` 呼び出し → `CREATE IF NOT EXISTS` のメタデータ読取が毎回発生（微オーバーヘッド、6,000 件規模では許容） |
| ボトルネック移行点 | **件数よりプロセス並行と WAL 未設定**が先に問題化。10 万行・数百 MB 超でバックアップ時間・`load_processed_ids` メモリ（全 ID set）を再評価 |

## 推奨アクション

- [ ] **P0**: `get_connection()` に `PRAGMA journal_mode=WAL` と `timeout=30.0`（秒）を明示設定し、同時アクセス時の `database is locked` を低減
- [ ] **P0**: `run_pipeline.bat` または `mail_pipeline.py` 先頭に **単一実行ロック**（Windows `msvcrt` / lock ファイル / `portalocker` 等）を追加し、スケジューラと手動実行の二重起動を防止
- [ ] **P0**: `insert_raw_email` を `INSERT ... ON CONFLICT(message_id) DO UPDATE` に統一し、SELECT→INSERT の TOCTOU と IntegrityError を排除
- [ ] **P1**: `migrate_processed_ids_json` を **1 トランザクション + commit 成功後のみ move** のまま、失敗時は `ensure_raw_inbox_ready` で **移行未完を ERROR 終了**（または processed 件数と json 件数の照合）に変更し、サイレント継続をやめる
- [ ] **P1**: `CREATE INDEX IF NOT EXISTS idx_raw_emails_processed ON raw_emails(processed)` を追加（`load_processed_ids` 用。6,000 件では効果小だが低コスト）
- [ ] **P1**: `message_id TEXT NOT NULL` をスキーマに追加（新規 DB は ALTER、既存はマイグレーションスクリプト）し、ゴースト行のデータ品質を向上
- [ ] **P2**: 年次アーカイブ方針（例: 12 ヶ月超の `body_text` を別テーブル/ファイルへ退避）を Phase 3 以降の設計に明記
- [ ] **P2**: 移行中間クラッシュ・二重 `migrate_processed_ids_json` 呼び出しの pytest を追加


---
R07_pipeline_classify.md
---

# R07: mail_pipeline 分類ロジック調査
調査日: 2026-06-18

## 結論（1行）
Phase 2のRecall重視化は事務・ヘルプデスク案件の取りこぼし解消に有効だが、`ENGINEER_PATTERNS`の`【BTM|【NBW`誤マッチと請求書・契約書のskip欠落が案件漏れ・ノイズの主リスク。

## 分類パターン一覧

### classify_system プロンプト全文（mail_pipeline.py L603-624）

```
あなたはSES業界のメール分類AIです。
件名と本文冒頭からemail_typeを判定し、JSONのみで返してください。

形式: {"type": "project"|"skip"}
※engineerは廃止。人員紹介メールはskipに統合

分類ルール:
- project: 業務委託・SES・派遣の案件情報。開発案件だけでなく、
  事務、ヘルプデスク、PMO、運用監視、キッティング、情シス支援、
  テスト、データ入力、コールセンター等も全て「project」。
  「案件」「募集」「○万」「○月〜」等のキーワードがあればproject。
  迷ったらprojectにする（Recall最優先）。
- skip: 以下は全てskip
  ・エンジニア/技術者/人材の紹介メール（「弊社エンジニア」「要員ご紹介」等）
  ・セミナー案内、メルマガ、配信停止通知、自動返信
  ・営業挨拶（案件情報なし）、求人広告、ニュースレター
  ※人員は松野/岡本がLINE経由で手動登録するため、配信の人員紹介は不要

SES業界用語:
- BP/プロパー/商流/稼働/並行 = SES業界の一般用語
- 案件 = 業務委託の仕事依頼
- 要員/人材 = エンジニア紹介
```

### analyze_final.py ルールベース判定（全列挙）

**判定関数 `classify_by_rule(subj, frm)` の優先順位: skip → engineer → project → unknown**

| カテゴリ | パターン | 検索対象 |
|---|---|---|
| SKIP (5) | セミナー\|ウェビナー\|説明会\|メルマガ\|配信停止\|プレスリリース\|ニュースレター | subj + frm |
| SKIP | 自動返信\|Auto-Reply\|Out of office\|自動応答\|不在通知 | subj + frm |
| SKIP | サービス.*ご紹介\|導入事例\|資料請求\|無料.*トライアル\|キャンペーン | subj + frm |
| SKIP | 採用情報\|正社員募集\|求人.*正社員\|転職.*支援 | subj + frm |
| SKIP | 営業挨拶\|ご挨拶のみ | subj + frm |
| ENGINEER (21) | 【直人材】\|【直要員】\|【直個人】\|【直BP】\|【SPONTO直個人】 | subj + frm[:50] |
| ENGINEER | 【弊社\|弊社.*プロパー\|弊社.*社員\|弊社.*フリー\|弊社.*個人\|弊社実績 | subj + frm[:50] |
| ENGINEER | 【要員】\|【人材】\|【要員配信】\|【人材情報】\|注力要員\|人材情報\|要員ご紹介 | subj + frm[:50] |
| ENGINEER | 弊社エンジニア\|技術者.*ご紹介\|エンジニア.*ご紹介 | subj + frm[:50] |
| ENGINEER | 【Astro人材】\|【プラウド要員】\|【KAD\|【ビズリンク\|【GLITTERS\|**【BTM\|【NBW**\|【アイル要員\|【SPONTO\|【実績あり所属 | subj + frm[:50] |
| ENGINEER | [／/](?:[0-9]+歳\|[0-9]+年).*(?:男性\|女性) | subj + frm[:50] |
| ENGINEER | (?:男性\|女性)／.*(?:万円\|万$\|\d+万) | subj + frm[:50] |
| ENGINEER | 即日.*(?:要員\|参画\|稼働)\|(?:要員\|参画).*即日\|稼働.*可能\|空き.*あり | subj + frm[:50] |
| ENGINEER | 【即日要員】\|即〜【\|即日【 | subj + frm[:50] |
| ENGINEER | 【[0-9]月.*要員】\|[0-9]月.*要員.*紹介\|要員.*[0-9]月 | subj + frm[:50] |
| ENGINEER | 【(?:Java\|Python\|…\|Tableau).*[0-9]+年】 | subj + frm[:50] |
| ENGINEER | (?:Java\|Python\|…\|COBOL).*[／/][0-9]+歳 | subj + frm[:50] |
| ENGINEER | [0-9]+万.*エンジニア\|エンジニア.*[0-9]+万\|[～〜~][0-9]+万\|… | subj + frm[:50] |
| ENGINEER | @[0-9]+万\|／[0-9]+万\|・[0-9]+万\|/[0-9]+万 | subj + frm[:50] |
| ENGINEER | 単価下げ\|条件緩和\|単価調整\|単価.*相談 | subj + frm[:50] |
| ENGINEER | 常駐可.*(?:弊社\|当社\|PM\|PMO\|Java\|インフラ)\|【実績あり | subj + frm[:50] |
| ENGINEER | [A-Z]{2,4}[0-9]{3,4}のご紹介\|のご紹介です | subj + frm[:50] |
| ENGINEER | ★大特価\|大特価 | subj + frm[:50] |
| ENGINEER | 【Java/C#人材】\|【Java.*人材】\|【.*人材】(?=.*万) | subj + frm[:50] |
| ENGINEER | 増員枠\|弊社増員 | subj + frm[:50] |
| PROJECT (12) | 【案件】\|【案件情報】\|【PJ】\|【プロジェクト】\|【求人】 | **subjのみ** |
| PROJECT | 案件.*募集\|募集.*案件\|案件.*紹介\|紹介.*案件 | subjのみ |
| PROJECT | CONVICTION案件\|NBW案件\|BTM案件\|【.*案件情報】\|【.*注力案件】\|【.*案件一覧】\|ICD案件 | subjのみ |
| PROJECT | 【.*(?:開発\|設計\|構築\|運用\|保守\|移行\|刷新\|導入\|リプレース\|DX\|PMO\|ヘルプデスク\|キッティング\|情シス\|テスト\|データ入力\|監視).*】 | subjのみ |
| PROJECT | 元請け\|直案件\|エンド直\|元請直\|エンド顧客\|現場直\|商流 | subjのみ |
| PROJECT | [0-9]+月[〜～~/\-] | subjのみ |
| PROJECT | **[0-9]+万** | subjのみ |
| PROJECT | ヘルプデスク\|PMO\|コールセンター\|事務\|運用監視\|キッティング\|情シス\|データ入力 | subjのみ |
| PROJECT | ≪急募≫\|《急募》\|★.*ICD案件 | subjのみ |
| PROJECT | COBOL案件\|汎用系.*案件\|若手歓迎.*案件 | subjのみ |
| PROJECT | 業務委託\|SES\|派遣 | subjのみ |

### 事業ルール照合表

| パターン | ルール判定 | LLM判定 | 正しい分類 | 実装OK? |
|---|---|---|---|---|
| SES案件メール（開発） | project（【案件】等） | project | project | OK |
| ヘルプデスク・事務 | project（ヘルプデスク\|事務等） | project | project | OK（Phase 2で改善） |
| PMO・コンサル | project（PMO等） | project | project | OK |
| 急募 | project（≪急募≫等） | project | project | OK |
| 面談設定済み | unknown→LLM | project（Recall） | project | △（件名に面談キーワードなし） |
| 人員紹介（【要員】等） | engineer→**skip** | skip | skip | OK |
| 人員紹介（弊社エンジニア） | engineer→skip | skip | skip | OK |
| BTM/NBWブランド**案件** | **engineer→skip**（`【BTM`/`【NBW`誤マッチ） | —（LLM未到達） | project | **NG** |
| 営業メール・広告 | skip（セミナー/メルマガ等） | skip | skip | OK |
| 自動返信 | skip | skip | skip | OK |
| 請求書・契約書 | unknown→LLM | skip（指示あり） | skip | △（ルール未カバー、LLM依存） |
| 自社内部メール | unknown→LLM | 不明（挨拶のみ） | skip | △（専用パターンなし） |
| 正社員求人 | skip | skip | skip | OK |
| 地方案件 | unknown→LLM | project（Recall） | project | OK（旧版は地方=skipで漏れ） |
| ロースキル・コールセンター案件 | project | project | project | OK（旧版はskipで漏れ） |
| 案件+人材混在メール | **engineer優先→skip** | — | project（案件部分） | **NG**（取りこぼし） |
| 挨拶のみ（お世話になっております） | unknown→LLM | project（Recall指示） | skip | △（ノイズリスク） |

## 人員紹介メールのskip判定

### ルール側
- `ENGINEER_PATTERNS`（21パターン）で件名+送信者先頭50文字を検索
- マッチ時は `classify_email_v2` で即 `{"type":"skip"}`（LLM分類をスキップ）
- 主なキーワード: 【要員】【人材】、弊社エンジニア、年齢/性別/万円の組み合わせ、即日要員、スキル+年数ブラケット等

### LLM側
- `classify_system` に明示: 「エンジニア/技術者/人材の紹介メール → skip」「要員/人材 = エンジニア紹介」
- LLM分類結果で `engineer` / `other` / `skip` はすべて `skip` に正規化（L758-759）

### すり抜けパターン（案件と人員混在）
1. **優先順位問題**: `classify_by_rule` は engineer を project より先に判定。件名に【要員】と【案件】が両方ある場合、engineer→skipとなり案件部分が捨てられる
2. **BTM/NBW案件の誤判定**: `【BTM案件】` / `【NBW案件】` が `【BTM` / `【NBW` パターンに先行マッチし、案件メールがskip化（**重大**）
3. **本文のみに人員情報**: ルールは件名のみ（PROJECT）または件名+送信者（ENGINEER）。件名が無難で本文に要員情報のみの場合、unknown→LLM。Recall指示によりproject誤判定の可能性
4. **engineer_system は残存**: コード上は未使用（v6.0 mainでengineer登録なし）だが、Batch APIフォールバック `classify_email()` は依然3分類（project/engineer/other）

## Phase 2緩和の影響分析

Phase 2 = v6.0改修（`done_tasks/20260618_180907_pipeline_full_intake.md`）。旧版は `analyze_v3.py` / `mail_pipeline.py.bak_phase4` を基準に比較。

### 旧SKIP → 新PROJECT になったカテゴリ

| 旧（skip） | 新（project/unknown→LLM project） | 根拠 |
|---|---|---|
| 地方案件（関西・大阪・福岡等） | unknown→LLM project | SKIP_PATTERNSから地方削除 |
| ロースキル・未経験可・アポ取り | project | SKIPから削除、PROJECTにヘルプデスク等追加 |
| コールセンター（業務系） | project | 同上 |
| ヘルプデスク・事務・情シス・キッティング | project | PROJECT_PATTERNSに明示追加 |
| PMO（単独） | project | PROJECT_PATTERNSに追加 |
| `[0-9]+万` のみの件名 | project（ルール） | PROJECT_PATTERNS新規追加 |
| `[0-9]+月〜` のみの件名 | project（ルール） | PROJECT_PATTERNS新規追加 |
| SES/派遣/業務委託 | project（ルール） | PROJECT_PATTERNS新規追加 |
| LLM: 迷った場合 | 旧: other/skip | 新: **project（Recall最優先）** |

### 緩和しすぎてノイズが入るケース

| リスク | 説明 |
|---|---|
| Recall指示の過剰project化 | 「迷ったらproject」により挨拶のみ・社内連絡がNotion登録される可能性 |
| `[0-9]+万` projectルール | 件名に万円のみで業務内容不明でもproject確定（ただしengineerが先に判定されるため人員系は除外） |
| `業務委託\|SES\|派遣` | 契約・請求関連メールの件名に「業務委託契約」等が含まれるとproject誤判定の可能性 |
| 請求書・契約書 | 旧v6.16には `SUBJECT_SKIP_PATTERNS`（請求書/契約書等）があったが、**現行v6.0のanalyze_finalには未移植** |
| Batchフォールバック | API障害時 `classify_email()` が旧3分類プロンプトに戻り、engineer/other処理が不整合 |

## エッジケース分析

| ケース | 現行の挙動 | 問題 |
|---|---|---|
| 件名が空 | ルール: unknown → LLM分類（件名空+本文100字） | 本文依存。Recall指示でproject化リスク |
| 本文が極端に短い | ルール: 件名のみ判定。LLM: body[:100] | 本文情報がほぼ使えない |
| HTML onlyメール | `get_body_and_attachments()` は **text/plain のみ**取得。HTMLフォールバックなし | body="" → 件名のみ依存。HTML主体メールは分類精度低下 |
| 転送（Fw:）/ 返信（Re:） | プレフィックス除去なし。件名そのままマッチ | 通常は問題少。元件名のパターンは有効 |
| 添付のみ・本文なし | body=""、添付は分類に未使用 | 件名が無難だとunknown→LLM。スキルシート添付の人員メールはすり抜け可能性 |
| BTM/NBW案件メール | engineer誤マッチ→skip | **案件取りこぼし（確認済みパターン）** |
| API Key未設定 | `classify_email()` フォールバック（旧3分類） | project/skip 2値運用と不整合 |
| Batch API障害 | 同上フォールバック | 分類基準が一時的に旧版に戻る |

## LLM分類とルール分類の競合時の優先順位

```
classify_email_v2 フロー:

1. classify_by_rule(subject, sender)
   ├─ skip      → 即 skip（LLM不要）
   ├─ engineer  → 即 skip（LLM不要）※v6.0でengineer=skip統合
   ├─ project   → 即 project構造化（classify LLM不要、extract LLMのみ）
   └─ unknown   → classify_system LLM（body[:100]）

2. LLM classify結果（unknownのみ）
   ├─ skip / other / engineer → skip
   └─ project → project構造化（第2バッチ）

優先原則: ルール判定が先。ルールで確定した場合LLMは呼ばれない。
→ ルール誤判定（BTM案件→engineer等）はLLMで救済されない。
```

mainループ（L1583-1587）での最終処理:
- `info.get("type")` が `engineer` の場合も `skip` に正規化
- `project` のみ Notion登録・マッチング実行
- それ以外（skip/other/error）は破棄

## 推奨アクション

- [ ] **P0**: `ENGINEER_PATTERNS` の `【BTM|【NBW` を `【BTM要員|【BTM人材|【NBW要員|【NBW人材` 等に限定し、`【BTM案件】`/`【NBW案件】` の誤skipを修正
- [ ] **P0**: 件名に `案件` を含む場合は engineer より project を優先する例外ルールを `classify_by_rule` に追加（混在メール対策）
- [ ] **P1**: v6.16にあった `SUBJECT_SKIP_PATTERNS`（請求書・契約書・勤怠・見積等）を `SKIP_PATTERNS` に復活
- [ ] **P1**: `get_body_and_attachments()` に text/html → プレーンテキスト変換フォールバックを追加（HTML onlyメール対策）
- [ ] **P2**: Batchフォールバック `classify_email()` を現行2値プロンプト（classify_system）に統一
- [ ] **P2**: `Fw:`/`Re:`/`[再送]` プレフィックス除去を分類前に実施
- [ ] **P2**: 分類精度モニタリング — raw_inbox.db の `classify_result` + `note` フィールドでルール/LLM別の誤判定率を週次集計
- [ ] **P3**: Recall指示を「案件キーワード（案件/募集/万/月〜/SES）がない挨拶のみはskip」に細分化し、ノイズ登録を抑制


---
R08_pipeline_notion.md
---

# R08: mail_pipeline Notion書き込み調査
調査日: 2026-06-18

## 結論（1行）
新4フィールドは `project_system` プロンプトと `register_project()` へのマッピングは実装済みだが、プロンプト指示が薄い・パース後バリデーションなし・あいまい表現未対応・フォールバック経路のスキーマ欠落・Notion書き込みが `common/notion_register.py` 未使用（429リトライ/案件名重複upsertなし）のため、案件情報の構造化品質と登録信頼性に複数の劣化リスクが残る。

## 新4フィールドの抽出精度
| フィールド | プロンプト指示 | バリデーション | Notion型 | 問題点 |
|---|---|---|---|---|
| job_category | JSONスキーマに10値enum + 1行の日本語対応表（`mail_pipeline.py:625-627`）。例: `development\|infrastructure\|...` ↔ 開発/インフラ/PMO… | `VALID_JOB_CATEGORIES` 外は `"other"` に丸め（`1194-1196`）。型・必須チェックなし | select（プロパティ名 `職種カテゴリ`、option名は英語slug） | 日本語→英語slug変換の明示ルールなし。複合案件（開発+インフラ）の優先順位なし。既存DBに別option名がある場合 `ensure_project_db_properties` は追加のみで既存selectを更新しない |
| age_limit | スキーマに `"age_limit":""` のみ。設計書（`done_tasks/20260618_180907`）の例（40代まで/年齢不問等）はプロンプト未反映 | なし。空文字はそのままスキップ（`add_rich_text_if_exists`） | rich_text（`年齢制限`） | 「〜50歳」「50代まで」「年齢不問」「不問」等の正規化なし。本文2000字切り詰めで年齢情報が後半のみの場合に欠落リスク |
| headcount | スキーマ default `1`。具体抽出ルールなし | `int(headcount)` のみ（`1200-1205`）。失敗時 `pass` でサイレント破棄。`if headcount` により `0` も未書き込み | number（`募集人数`） | 「若干名」「複数名」「数名」等のあいまい表現は数値化不可でフィールド欠落。不明時もLLMがdefault `1` を返しやすく偽陽性リスク |
| commercial_flow | スキーマに `"commercial_flow":""` のみ。設計書の例（元請直/1社先まで等）はプロンプト未反映 | なし | rich_text（`商流`） | CEO指示書は「商流判定はシステム側不要（成約後手動）」と矛盾。BP/商流は分類プロンプトに用語としてあるが抽出指示なし |

**プロンプト全文（`project_system`）:**

```
SES案件メールから情報をJSONのみで返してください。
{"type":"project","name":"案件名","job_category":"development|infrastructure|pmo|helpdesk|office|testing|operations|data|sap|other","required_skills":[],"optional_skills":[],"price":0,"start_date":"","location":"","remote":"不明","period":"","interview_count":1,"foreign_ok":false,"age_limit":"","headcount":1,"commercial_flow":"","note":"業務内容"}
job_category: 開発/インフラ/PMO/ヘルプデスク/事務/テスト/運用/データ/SAP/その他
価格は万円単位の整数。不明な項目は空文字または0。
```

**既存フィールドとの整合性（抜粋）**
- `required_skills` / `optional_skills`: `VALID_SKILLS` ホワイトリストでフィルタ（`1179-1184`）— 新4フィールドより厳格
- `price`: 円/万円の自動変換あり（`1185-1189`）
- `start_date`: ISO `YYYY-MM-DD` のみ Notion `開始日` に書込（`1190-1191`, `is_valid_iso_date`）
- `remote` / `period` / `interview_count` / `foreign_ok`: プロンプトに含まれるが **`register_project()` でNotion未マッピング**（構造化後に破棄）
- フォールバック `classify_email()`（`570-588`）は旧スキーマで **新4フィールドなし** — Batch API失敗時に全フィールド欠落

## Notion書き込みフロー

```
メール取得 (IMAP, msg_id重複除去)
  → raw_inbox.db 全件保存
  → processed フラグで未処理のみ抽出
  → classify_email_v2 (Batch API)
       ├ ルール分類 project → build_extract_request(project_system)
       └ 要分類 → classify_system → project なら extract
       ※例外時 classify_email() フォールバック（旧スキーマ）
  → parse_json_text(): ```除去 → json.loads → dict以外は {"type":"other"}
  → register_project(info, ...)
       ├ ensure_project_db_properties()  # 起動時に4プロパティ自動追加
       ├ properties 組み立て（案件名/詳細/スキル/単価/開始日/勤務地/新4/入力元/元MessageID/原文）
       ├ validate_project_payload()  # 案件名titleのみ検証
       └ requests.post /v1/pages  # 一括create（部分書き込みなし）
  → 失敗時も finally で save_processed_id() → 再処理されない
  → 成功時: 添付保存 → Drive URL PATCH → マッチング → 下書き保存
```

**`ensure_project_db_properties()`（`848-875`）**
- `PROJECT_DB_REQUIRED_PROPERTIES` に定義された4プロパティがDBに無ければ `PATCH /databases/{id}` で追加
- 成功: キャッシュ更新 + ログ。失敗: ログのみで続行（リトライなし）
- DRY_RUN（`DRY_RUN=1` かつ `DRY_RUN_PROCESS_EMAILS!=1`）時はスキップ
- プロパティが存在しない場合、各 `add_*_if_exists` / headcount条件分岐で **該当フィールドは書き込まれない**（エラーにならない）

**プロパティ型マッピング**
| JSONキー | Notionプロパティ | 型 |
|---|---|---|
| job_category | 職種カテゴリ | select（英語slug） |
| age_limit | 年齢制限 | rich_text |
| headcount | 募集人数 | number |
| commercial_flow | 商流 | rich_text |

**重複チェック**
- メールレベル: `msg_id` のみ（SQLite `processed` フラグ、`1551`）。転送・再配信で Message-ID が変わると二重登録可
- Notionレベル: **なし**。`元MessageID` は rich_text として保存するだけで登録前クエリに未使用
- 参考: `common/notion_register.py` は `案件名` + `入力元` で upsert + 429リトライを実装済みだが、**mail_pipeline は未使用**（常に新規 create）

## エラーハンドリング

| 障害パターン | 現状の処理 | 評価 |
|---|---|---|
| 認証エラー (401) | `register_project`: status!=200 → ログ + `return False`（`1228-1231`）。`ensure_project_db_properties`: ログのみ | **要改善** — 即時停止・通知なし |
| レート制限 (429) | mail_pipeline内の Notion 呼び出しに **リトライなし**（`requests.post/patch` 直叩き） | **要改善** — `common/notion_register._request_with_retry` と乖離 |
| タイムアウト | `ensure_project_db_properties` / `update_page_properties`: timeout=30s。`register_project` の page create は **timeout未指定**（`1223-1227`）。`notion_query`: timeout未指定 | **要改善** |
| JSONパース失敗 | `{"type":"other","note":"解析失敗"}` → project登録されず skip 扱い | 許容 |
| フィールド型不正 | job_category→other、headcount→破棄、その他はそのまま or スキップ | **要改善** — サイレント劣化 |
| 部分書き込み | 単一 page create のため発生しない（全プロパティ一括 or 全体失敗） | N/A |
| Notion登録失敗後 | `save_processed_id` を finally で必ず実行（`1680-1681`）→ **再処理不可** | **要改善** — データ欠損の永久化 |
| プロパティ未作成 | ensure失敗 → 該当フィールドは書かれずに他フィールドは登録成功しうる | **要改善** |
| select option不一致 | 職種カテゴリに未登録optionを指定すると API 400 の可能性 | **要確認**（実API未検証） |

**LLM側の制約（抽出精度に影響）**
- 抽出 `max_tokens=400`（`647`）、本文 `body[:2000]` — 長文案件で truncation
- Batch API タイムアウト 120分（`666-680`）、失敗時 `classify_email` フォールバック
- 日次コスト上限 `$2.0` で API スキップ（`532-534`）

## データ変換ステップと損失リスク

| ステップ | 変換内容 | 損失リスク |
|---|---|---|
| 1. メール本文 | 最大2000文字に切り詰め（`649`） | 後半の年齢・商流・人数情報欠落 |
| 2. LLM抽出 | JSON dict 生成 | プロンプト指示不足による誤抽出・default値（headcount=1） |
| 3. parse_json_text | 型検証なし | 配列/数値の型崩れが下流まで伝播 |
| 4. skills フィルタ | VALID_SKILLS 以外除去 | 意図的（スキル名正規化） |
| 5. register_project | フィールド別マッピング | remote/period/interview_count/foreign_ok 完全破棄 |
| 6. Notion write | プロパティ存在チェック | DBスキーマ不整合時にサイレントスキップ |
| 7. 案件詳細 rich_text | 件名+送信元+**全文raw_body** | 構造化失敗フィールドは原文に残るが検索・マッチング不可 |

**テスト状況**
- `tests/` に新4フィールド・`register_project` のユニットテスト **なし**
- `raw_inbox` / `metrics` / `recovery_mode` のみテストあり

## 推奨アクション
- [ ] **P0**: `register_project()` を `common/notion_register.register_project()` に委譲し、429/5xxリトライと `案件名+入力元` upsert を有効化
- [ ] **P0**: `classify_email()` フォールバックのスキーマを `project_system` と同期（新4フィールド + job_category指示）
- [ ] **P0**: `project_system` に age_limit / headcount / commercial_flow の抽出例とルールを追加（「若干名→null」「不明→空/0」「商流: 元請/1社先/2社先/3社先以降」等）
- [ ] **P1**: headcount 正規化関数を追加（「若干名」→null、「複数名」→null または備考追記、数値のみ number 書込）
- [ ] **P1**: `validate_project()` を新設（job_category enum、headcount 数値範囲、age_limit 最大長）し、REVIEW時は `案件詳細` に `[validation]` 追記
- [ ] **P1**: `register_project` の `requests.post` に `timeout=30` を付与。Notion登録失敗時は `processed` を立てない（または retry キュー化）
- [ ] **P1**: `元MessageID` による Notion 事前クエリで同一メールの二重登録を防止
- [ ] **P2**: `remote` / `period` / `interview_count` / `foreign_ok` の Notion プロパティマッピングを追加（DBにプロパティが存在する場合のみ書込）
- [ ] **P2**: 新4フィールドのユニットテスト追加（プロンプト→parse→properties 変換の fixture テスト）
- [ ] **P2**: `ensure_project_db_properties` 失敗時にメトリクス `notion_schema_errors` を計上し LINE 通知に含める


---
R09_pipeline_imap.md
---

# R09: mail_pipeline IMAP・並行安全性調査
調査日: 2026-06-18

## 結論（1行）
IMAPは7日間SINCE＋アカウント別最新200件取得・Message-IDで重複排除・1回50件処理だが、接続リトライ・IMAPタイムアウト・アプリ内ロックがなく、スケジューラ二重系と「例外でもfinallyでprocessed化」により取りこぼし・見逃しリスクが残る。

## IMAP接続設定

| 項目 | 実装値 | 根拠 |
|---|---|---|
| サーバー / ポート | `mail65.onamae.ne.jp:993`（デフォルト） | `mail_pipeline.py:100-101` `OUTLOOK_IMAP_SERVER` / `OUTLOOK_IMAP_PORT` |
| プロトコル | `imaplib.IMAP4_SSL` | `mail_pipeline.py:429` |
| SSL/TLS | `ssl.create_default_context()` + **`check_hostname=False` / `verify_mode=CERT_NONE`** | `mail_pipeline.py:425-427`（証明書検証無効） |
| 接続タイムアウト | **未設定**（`imaplib` デフォルト＝事実上無制限） | `fetch_emails_from_account()` に `socket` / `timeout` 指定なし |
| リトライ | **なし**（1回失敗で `return []`） | `mail_pipeline.py:432-434` |
| 認証情報 | `config/.env` → `dotenv_values` で `os.environ` へ投入 | `mail_pipeline.py:73-98, 102-120` |
| アカウント | 共通（`OUTLOOK_EMAIL`/`OUTLOOK_PASSWORD`）＋任意で松野・岡本 | `EMAIL_ACCOUNTS` 配列 |
| 対象フォルダ | `INBOX` のみ | `mail_pipeline.py:431` |

**認証の取得経路**

```
config/.env
  OUTLOOK_IMAP_SERVER, OUTLOOK_IMAP_PORT
  OUTLOOK_EMAIL, OUTLOOK_PASSWORD
  MATSUNO_EMAIL, MATSUNO_PASSWORD（任意）
  OKAMOTO_EMAIL, OKAMOTO_PASSWORD（任意）
```

ハードコードはサーバー名・ポートのデフォルト値のみ。パスワードはコード内にない。

**接続失敗時の挙動**

- ログ `IMAP接続エラー ({user}): {e}` を出し、そのアカウント分は空リスト
- 他アカウントは継続
- **`metrics.imap_errors` はインクリメントされない**（フィールド定義のみ、`mail_pipeline.py` 内で `inc("imap_errors")` 呼び出しなし）

## フェッチ・処理フロー

### FETCH_LIMIT=200 / PROCESS_LIMIT=50

| 定数 | 値 | 適用箇所 |
|---|---|---|
| `FETCH_LIMIT` | 200 | `main()` → `fetch_recent_emails(limit=fetch_limit)` |
| `PROCESS_LIMIT` | 50 | `new_emails[:process_limit]` |

`RECOVERY_MODE=true` 時のみ `recovery_state.json` のフェーズ別 limit で上書き（現状 `day0_emergency`: fetch=50, process=10）。通常は定数 200/50。

### フェッチ条件（UNSEEN ではない）

```python
# mail_pipeline.py:436-446
since_date = (date.today() - timedelta(days=7)).strftime("%d-%b-%Y")
status, messages = mail.search(None, f"SINCE {since_date}")
target_ids = list(reversed(all_ids[-limit:]))  # 7日以内のうち最新 limit 件
```

- **未読（UNSEEN）ではない** — 直近7日の全メールから最新200件（アカウントごと）
- 3アカウント合計最大約600件（`msg_id` で重複除去後）
- 古い SPEC.md の「UNSEENのみ」は現行 v6.0 と不一致

### 200件フェッチ → 50件処理 → 残りの扱い

```
fetch_recent_emails(200/アカウント)
  → raw_inbox.db に全件 INSERT（新規のみ）
  → load_processed_ids() で processed=1 の Message-ID を除外
  → new_emails[:process_limit] のみ LLM分類・Notion等
  → ループ finally で save_processed_id()（processed=1）
```

- **残りの new_emails（51件目以降）は次回実行で再対象**（processed フラグ未設定のため）
- **ただし次回も同じ200件ウィンドウ内に収まる必要あり** — 7日以内に200件超の新着が続くと、古い未処理メールはフェッチ対象外になり取りこぼしうる

### 再フェッチ防止

| 層 | 仕組み |
|---|---|
| 処理済み判定 | SQLite `raw_emails.processed=1`（旧 `processed_ids.json` は起動時マイグレーション） |
| キー | RFC `Message-ID` ヘッダ（無い場合は `no-id-{imap_seq}-{user}`） |
| マルチアカウント重複 | `fetch_recent_emails` 内で `msg_id` の `seen_ids` セット |
| raw保存 | フェッチ直後に `insert_raw_email`（分類前）— 取りこぼしゼロ基盤 |

### processed 判定タイミング

| タイミング | 内容 |
|---|---|
| フェッチ時 | **processed にはしない**（raw_inbox に `processed=0` で保存のみ） |
| 分類後 | `update_classify_result()` で `classify_result` 更新 |
| 各メール処理後 | **`finally` で必ず `save_processed_id()`** — 成功・失敗・例外問わず |
| Notion失敗時 | `register_project` 失敗でも `save_processed_id` 後 `continue`（再処理されない） |
| 途中クラッシュ | Python プロセスごと落ちた場合、そのメールは processed 未設定 → **次回再処理** |
| 例外スキップ | `except` でログ後 `finally` が走るため **processed 化され再処理されない**（欠落リスク） |

**トレードオフ（SPEC_costfix 意図）**: 無限再処理ループ防止のため「例外でも processed」だが、分類・Notion未完了メールは永久スキップになりうる。raw_inbox には本文が残る。

## 並行実行安全性

### mail_pipeline.py 本体

- **PIDファイル / flock / SQLiteロックなし**
- 同一 `raw_inbox.db` への同時書き込みは SQLite のデフォルト挙動に依存（明示排他なし）

### スケジューラ側

| 機構 | 設定 | 効果 |
|---|---|---|
| Windows タスク `SES_MailPipeline` | `MultipleInstancesPolicy: IgnoreNew` | 前回実行中は新インスタンス起動を無視 |
| 同上 | `ExecutionTimeLimit: PT1H` | 1時間で強制終了 |
| `local_server/scheduler.py` | `job_state/mail_pipeline_hourly.lock`（PIDファイル, O_EXCL） | 時間軸スケジューラ内の二重起動防止 |
| 同上 | `threading.Lock` + `is_running()` | 同一プロセス内の重複実行防止 |

**二重スケジューラ共存**

1. **Windows Task Scheduler** — 初回登録は30分間隔（`schtasks /mo 30`）。バックアップ XML（2026-06-18）は **1時間間隔（PT1H）** で `wd_mail_pipeline.bat` 実行
2. **`local_server/scheduler.py`** — command_server 起動時に **毎時** バックグラウンド実行（catch-up 最大3スロット）

両方が有効だと、別経路から同時起動しうる。タスク側 `IgnoreNew` と scheduler 側 PID ロックは**相互に認識しない**。

### 30分（または1時間）間隔 × 処理30分超

`job_state/mail_pipeline_hourly.json` の実績例:

- 15:00 開始 → 15:49 終了（約49分）
- 17:00 開始 → 17:35 終了（約35分）

`IgnoreNew` のため、処理が次スロットをまたぐと **そのスロットの実行はスキップ**（ログに残らない）。バックログは次回の `new_emails[:50]` で徐々に消化する設計だが、スキップされたスロット分の「追加取得」は発生しない。

## 17時間スキップ再発リスク

### 既知事故（調査指示の「17時間」≒ 社内記録の16時間）

- **期間**: 2026-06-17 20:00 〜 2026-06-18 11:00（約15〜16時間、`wall_hitting_bugs_round5`）
- **最有力原因**: PCスリープ中のトリガー喪失 + `StartWhenAvailable` 未設定（または false）+ `UseUnifiedSchedulingEngine=true`
- **副次要因**: 2026-06-18 11:54 の `Set-ScheduledTask`（RestartCount=3 追加）直後、12:00 トリガーがスキップされた事例

### タスクスケジューラ設定（バックアップ XML 時点）

| 設定 | 値 | 再発リスク |
|---|---|---|
| 実行中の場合 | `IgnoreNew` | 長時間実行中は次回丸ごとスキップ |
| `RestartCount` / `RestartInterval` | バックアップ XML に**記載なし**；6/18 に `RestartCount=3`, `PT1M` 追加作業あり | 起動失敗時の再試行は設定済みの可能性（要実機確認） |
| `StartWhenAvailable` | バックアップ XML に**記載なし**（デフォルト false 想定） | スリープ復帰後の未実行補填なし → **高リスク** |
| `DisallowStartIfOnBatteries` | true | バッテリー駆動時は起動しない |
| 実行ラッパー | `weekday_guard.py` → 土日祝は **exit 0 で即終了** | 休日は意図的スキップ |

### 長時間未実行の検知・アラート

| 機構 | 有無 |
|---|---|
| `metrics.jsonl` + 実行後 LINE push | あり（毎回）— 未実行そのものは検知しない |
| `metrics_daily_summary.py` | 23:00 日次サマリー — **実行回数ゼロは「データなし」表示のみ** |
| `job_state/mail_pipeline_hourly.json` | `last_success_at`, `last_skipped_slot` — scheduler 経由のみ |
| ギャップ検知（例: 2時間以上未実行でアラート） | **なし** |
| catch-up | `scheduler.py` で最大3時間分補填 — **Task Scheduler 経路には未適用** |

## 推奨アクション

- [ ] **IMAP接続に `socket.setdefaulttimeout(60)` または `IMAP4_SSL(..., timeout=60)` を追加**し、ハングを防止する
- [ ] **IMAP接続失敗時に指数バックオフで2〜3回リトライ**し、失敗時は `metrics.inc("imap_errors")` を記録する
- [ ] **`fetch_emails_from_account` 失敗時に exit_code≠0 または LINE 異常通知**（現状は空リストで正常終了しうる）
- [ ] **7日×200件ウィンドウ外の未処理検知** — `raw_inbox` で `processed=0` かつ `received_at` が古い件数を metrics / 日次サマリーに出す
- [ ] **例外時の processed 方針を見直し** — `finally` 一括 processed をやめ、Notion成功時のみ processed、または `processed` と `classify_result='error'` を分離して再処理可能にする
- [ ] **スケジューラを一本化**（Task Scheduler **または** `local_server/scheduler.py`）し、二重起動経路をなくす
- [ ] **Task Scheduler に `StartWhenAvailable=true` を管理者権限で設定**し、スリープ復帰後の missed trigger を回収する
- [ ] **タスク更新は次回トリガーの15分以上前に限定**（11:54更新→12:00スキップの再発防止）
- [ ] **長時間未実行アラート** — `last_success_at` から90分以上経過で LINE 警告（`job_state` または `metrics.jsonl` 最終行を監視）
- [ ] **`RECOVERY_MODE` 無効時も `recovery_state.json` と実 limit の乖離をドキュメント化**（調査時点: 定数200/50が有効、recovery_state の 50/10 は `RECOVERY_MODE=true` 時のみ）


---
R10_pipeline_test_coverage.md
---

# R10: mail_pipeline テスト・エラー処理調査
調査日: 2026-06-18

## 結論（1行）
pytest 35件は全パス（4 skip）だが `mail_pipeline.py` 本体・Batch API・IMAP/Notion 経路はほぼ無テストで、CostGuard v2 / `DAILY_CALL_LIMIT` 未統合・`main()` が exit code を返さないなど本番障害リスクが残存。

## テスト実行結果
| テストファイル | Pass | Fail | Skip |
|---|---|---|---|
| test_analyze_final.py | 4 | 0 | 0 |
| test_metrics_recorder.py | 6 | 0 | 0 |
| test_notion_engineer_payload.py | 4 | 0 | 4 |
| test_raw_inbox.py | 6 | 0 | 0 |
| test_recovery_mode.py | 11 | 0 | 0 |
| **合計** | **31** | **0** | **4** |

**スキップ詳細（4件）**: `test_notion_engineer_payload.py` の `test_case_a`〜`test_case_d` — `RUN_NOTION_LIVE_TESTS=1` 未設定のため本番 Notion API テストをスキップ。

**失敗テスト**: なし。

**テストケース数**: 35件（Pass 31 + Skip 4）。

## カバレッジ不足箇所
| モジュール | テストなし関数 | リスク |
|---|---|---|
| `mail_pipeline.py` | `call_claude`, `classify_email`, `classify_email_v2`（Batch API 含む）, `extract_affiliation`, `ai_matching`, `double_check` | LLM 分類・マッチング・ダブルチェックの本番経路。CostGuard 漏れ・JSON パース失敗時のサイレント劣化 |
| `mail_pipeline.py` | `fetch_emails_from_account`, `fetch_recent_emails`, `decode_str`, `get_body_and_attachments` | IMAP 接続・メール解析の障害がテストで検知不可 |
| `mail_pipeline.py` | `register_project`, `register_engineer`, `notion_query`, `update_page_properties`, `send_proposal_email` | Notion/SMTP 書き込み失敗・payload 不整合が本番初出 |
| `mail_pipeline.py` | `main`, `_main_body`, `_save_all_emails_to_raw_inbox`, `_push_metrics_line`, `_handle_recovery` | オーケストレーション全体・DRY_RUN 分岐・メトリクス/LINE push |
| `mail_pipeline.py` | `get_today_cost_usd`, `filter_engineers_by_skills`, `process_skill_sheet`, `save_draft` | コストガード判定・スキルフィルタ・下書き生成の回帰検知なし |
| `raw_inbox.py` | `update_classify_result`, `count_rows`, `count_processed`, `body_hash`（直接） | 分類結果の DB 更新・統計集計の不整合 |
| `analyze_final.py` | `__main__` ブロック（コスト試算スクリプト） | 本番パイプライン非経路のため低リスク。`classify_by_rule` のみ 4 テストあり |

**テストあり（参考）**: `raw_inbox` 6関数、`recovery_mode` 全主要関数、`MetricsRecorder`、`classify_by_rule`（4パターン）、`validate_engineer_payload`（インライン実装コピーで検証 — 本物 `mail_pipeline.validate_engineer_payload` とは別実装）。

## CostGuard適用状況
| LLM呼び出し箇所 | CostGuard | モデル | max_tokens |
|---|---|---|---|
| `call_claude()` L530（`classify_email`, `extract_affiliation`, `ai_matching`, `double_check` 経由） | **部分** — `get_today_cost_usd() >= DAILY_COST_LIMIT_USD($2.0)` のみ。`cost_guard.py` / `ledger.reserve()` / `DAILY_CALL_LIMIT` **未使用** | `claude-haiku-4-5-20251001` | 50〜2000（呼び出し元依存） |
| `classify_email_v2()` → `send_batch()` L653（Batch API 直接 `requests.post`） | **なし** — 日次コストチェック・`log_cost()` 記録ともにバイパス | `claude-haiku-4-5-20251001` | 50（分類）/ 400（抽出） |
| `classify_email_v2()` フォールバック → `classify_email()` | 上記 `call_claude` の部分ガードのみ | 同上 | 1500（デフォルト） |

**補足**:
- OpenAI / `gpt-` / `responses.create` の呼び出しは `mail_pipeline/` 内に**なし**（Anthropic Haiku のみ）。
- 成功時は `usage_tracker.cost_logger.log_cost()` で `cost_log.jsonl` に記録されるが、Batch API 経路は記録されない。
- `cost_guard_v2/TASKS.md` 7.3「`mail_pipeline.py` を `cost_guard.allowed()` 経由に置換」は **未完了**。
- `DAILY_CALL_LIMIT=30`（`common/ledger.py` の `DAILY_CALL_LIMIT_DEFAULT`）は **mail_pipeline 未適用**。現行はドル上限 `$2.0/日`（`DAILY_COST_LIMIT_USD`）のみ。
- `get_today_cost_usd()` が例外時 `0.0` を返すため、ログ読み取り失敗時はガードが無効化される。

## エラーハンドリング評価

### try/except カバー範囲
- **広すぎる `except:`（バア except）**: `classify_email` L587、`ai_matching` L818 — JSON パース失敗を握りつぶし `other`/空候補を返す。意図的だがデバッグ困難。
- **メール単位の `except Exception`**: `_main_body` L1678 — 1件の失敗でスキップし `finally` で processed 化。パイプライン全体は継続（非致命的）。
- **`main()` トップレベル**: L1499 — 致命例外をキャッチし `metrics.finalize(exit_code=1)` するが、**`sys.exit()` を呼ばない**ためシェル/Task Scheduler は常に exit 0。

### ログ粒度
- エラーはほぼ `log(f"...: {e}")` の文字列のみ。**`traceback` / `exc_info` 未使用** — スタックトレースは `pipeline.log` に出ない。
- Batch API 失敗時は `RuntimeError`/`TimeoutError` を raise 後、外側でフォールバック（L779）— 原因は1行ログのみ。

### 致命的 vs 非致命的
| 種別 | 挙動 | 例 |
|---|---|---|
| 非致命的 | ログして継続 | IMAP 1件取得失敗、メール1件処理例外、Notion 1件登録失敗（`continue`） |
| 準致命的 | metrics `exit_code=1` 記録だがプロセスは 0 終了 | `main()` 未捕捉例外 |
| コスト上限 | API スキップ（空文字返却） | `call_claude` の `$2/日` 到達 |

### exit code
- `main()` / `if __name__ == "__main__"`: **`sys.exit` なし** — Task Scheduler・recovery_mode の `exit_code` 判定（metrics 内記録）と実プロセス終了コードが乖離。
- `exit(2)` の使用: **なし**。
- `test_raw_inbox.py`（tests 外のスタンドアロン）: `sys.exit(0|1)` あり。

### 設定値
| 設定 | 定義場所 | 変更容易性 |
|---|---|---|
| `FETCH_LIMIT=200`, `PROCESS_LIMIT=50` | `mail_pipeline.py` L82-83 定数 | コード変更が必要。`RECOVERY_MODE=true` 時は `recovery_mode.PHASE_SETTINGS` で上書き（day0: 50/10 → day3: 200/50） |
| `DAILY_COST_LIMIT_USD=2.0` | `mail_pipeline.py` L92 | コード変更が必要 |
| `MATCH_TOP_N=10` | L84 | コード変更が必要 |
| IMAP `since_days=7` | `fetch_emails_from_account` デフォルト引数 L419 | 関数引数で変更可（呼び出し元は固定 7） |
| Claude API timeout | L550,660,671: 60s / batch poll: 120min / results: 120s | ハードコード |
| Notion API timeout | L835,867,936: 30s | ハードコード |
| IMAP timeout | **未設定**（`imaplib` デフォルト） | — |

### DRY_RUN / DRY_RUN_PROCESS_EMAILS
| 条件 | 挙動 |
|---|---|
| `DRY_RUN=1` かつ `DRY_RUN_PROCESS_EMAILS≠1` | `_main_body` 冒頭で即 return — IMAP/Notion/送信すべてスキップ（起動確認のみ） |
| `DRY_RUN=1` | `update_page_properties`, `send_proposal_email`, `register_project`, `register_engineer` を個別スキップ |
| `DRY_RUN_PROCESS_EMAILS=1` | 上記早期 return をバイパスし、メール処理フローに入る（個別 DRY_RUN ガードは残る） |

## 推奨アクション
- [ ] **P0**: `classify_email_v2` の Batch API に `call_claude` 同等のコストガード + `log_cost()` 記録を追加（現状最大のコスト暴走経路）
- [ ] **P0**: `mail_pipeline.py` を `cost_guard.allowed()` / `finalize()` + `ledger.reserve(DAILY_CALL_LIMIT)` に統合（`cost_guard_v2/TASKS.md` 7.3 完了）
- [ ] **P0**: `main()` 終了時に `sys.exit(final_metrics.get("exit_code", 0))` を追加し、recovery_mode・Task Scheduler と整合
- [ ] **P1**: `mail_pipeline.py` コアのユニットテスト追加 — `call_claude`（モック）、`classify_email_v2`（Batch モック）、`filter_engineers_by_skills`、`get_today_cost_usd`
- [ ] **P1**: 裸 `except:`（L587, L818）を `except (json.JSONDecodeError, ValueError)` に限定し、予期しない例外はログ+再 raise
- [ ] **P1**: 致命/メール単位エラーに `traceback.format_exc()` または `logging.exception` を追加
- [ ] **P2**: `raw_inbox.update_classify_result` / `count_processed` のテスト追加
- [ ] **P2**: `test_notion_engineer_payload.py` の `_make_validate_fn` を本物 `mail_pipeline.validate_engineer_payload` インポートに差し替え
- [ ] **P2**: `FETCH_LIMIT` / `PROCESS_LIMIT` を環境変数化（`RECOVERY_MODE` 非活性時の運用柔軟性）


---
R11_attachment_importer.md
---

# R11: mail_attachment_importer 調査
調査日: 2026-06-18

## 結論（1行）
Phase 9 完了済みでパターン A/B/C のパイプラインは動作するが、型判定は拡張子のみ・`.xls`/`.doc` は実質非対応・`project_sheet_urls` は未配線・添付サイズ/パスワード保護の明示処理なしというギャップが残る。

## パターン別分析

### パターンA（添付ファイル）

**処理フロー**

```
mail_fetcher._fetch_new_emails_for_account()
  → Content-Disposition: attachment のパーツを走査
  → 拡張子が SUPPORTED_EXTS に一致するもののみ取得
importer.main() → process_attachments()
  → parsers.file_parser.parse_file() でテキスト化
  → 200文字未満は error カウントでスキップ
  → ai_extractor.classify_content() で engineer / project / unknown 判定
  → extract_engineers() または extract_projects()
  → utils.notion_writer.register_engineer() / register_project()
```

**対応形式**

| 拡張子 | パーサー | 実効性 |
|---|---|---|
| `.xlsx` | openpyxl (`data_only=True`, BytesIO 読み取り専用) | 良好 |
| `.xls` | openpyxl に委譲 | **要改善** — openpyxl は旧形式 `.xls` 非対応。例外 → `parse_file` が `None` 返却 |
| `.pdf` | pdfplumber | 良好（スキャンPDFはテキスト抽出不可の可能性） |
| `.docx` | python-docx | 良好 |
| `.doc` | python-docx に委譲 | **要改善** — 旧形式 `.doc` 非対応 |

**人員/案件の自動振り分け（Phase 8 追加）**

- `classify_content()` が LLM（`can_spend` 通過時）またはキーワードスコアリングで判定
- `engineer` → `extract_engineers` → エンジニア DB upsert（名前+所属）
- `project` → `extract_projects` → 案件 DB 登録（案件名重複チェック）
- `unknown` → skip カウント

**openpyxl creator metadata 上書き問題**

- 現行コードは `BytesIO` から **読み取りのみ**（`load_workbook(..., data_only=True)`）。保存処理は存在しない
- よって creator metadata の上書きリスクは **該当なし**（読み取り専用フロー）
- `data_only=True` は数式セルを計算結果として読むための設定であり、メタデータ対策ではない

### パターンB（単一URL）

**処理フロー**

```
mail_fetcher: 本文 _get_body_text() から SHEET_URL_PATTERN で URL 抽出
importer.main() → process_sheet_urls()
  → sheet_fetcher.fetch_sheet_text()（Playwright headless Chromium）
  → 50文字未満は error
  → extract_engineers()（1名分を想定）
  → register_engineer() × N
```

**パターン B と C のコード上の区別**

- **区別なし**。どちらも `process_sheet_urls()` → `extract_engineers()` の同一経路
- LLM が JSON 配列で返す人数に依存（1名なら B、複数名なら C）
- `test_mock_patterns.py` で B（1件）/ C（3件）をモック検証済み

**Spreadsheet URL 正規表現**

```python
SHEET_URL_PATTERN = re.compile(
    r'https://docs\.google\.com/spreadsheets/d/[A-Za-z0-9_\-]+[^\s\r\n"<>]*'
)
```

- `docs.google.com/spreadsheets/d/{ID}` 形式を本文から抽出
- `set()` で重複 URL を除去
- `/edit`, `/view`, `?gid=` 等のサフィックスも `[^\s\r\n"<>]*` で許容

**Playwright 取得**

- タイムアウト 15 秒、読み込み後 3 秒待機
- `accounts.google.com` / `ServiceLogin` リダイレクト → `login_required`（skip）
- 取得成功時テキスト上限 **50,000 文字**（`sheet_fetcher.py:47`）

### パターンC（複数人員リスト）

- パターン B と同一の `process_sheet_urls()` 経路
- `extract_engineers()` が複数要素の JSON 配列を返し、ループで `register_engineer()` を繰り返す
- スプレッドシート 1 URL に複数人がまとまっているケースを LLM 側で分解

**案件版 C（補足・未配線）**

- `importer.py` に `process_sheet_urls_projects()` と `project_sheet_urls` 分岐が存在
- しかし `mail_fetcher.py` は `project_sheet_urls` を **一切設定しない**
- スプレッドシート URL 経由の案件登録は現状 **到達不能（デッドコード）**
- 案件のスプレッドシート取込はパターン A（添付 + `classify_content` → project）でのみ可能

## 添付ファイルの型判定

| 方式 | 実装 | 評価 |
|---|---|---|
| 拡張子 | `Path(filename).suffix.lower()` と `SUPPORTED_EXTS` / `parse_file` の分岐 | **のみ使用** |
| MIME type | `part.get_content_type()` は参照せず | **未実装** |
| マジックバイト | なし | **未実装** |

**リスク**: `report.pdf` という名前の `.xlsx` ファイルは Excel パーサーで失敗し error になる。逆に拡張子偽装の検出もなし。

## CostGuard 適用（LLM 呼び出し箇所）

`common.ledger.can_spend()` / `record()` を `ai_extractor.py` で使用。

| 関数 | 推定トークン (in/out) | 上限到達時 | API 成功後 |
|---|---|---|---|
| `classify_content()` | 1000 / 50 | キーワード fallback（API キーなし時も同様） | `record()` |
| `extract_engineers()` | 2500 / 2000 | 空リスト `[]` 返却 | `record()` |
| `extract_projects()` | 2500 / 2000 | 空リスト `[]` 返却 | `record()` |

- グローバル上限: `COST_GUARD_DAILY_USD`（デフォルト $8）/ `COST_GUARD_MONTHLY_USD`（デフォルト $140）
- LLM 入力 truncate: classify 3000 文字、extract 8000 文字
- `reserve()` / フェーズ別 `DAILY_CALL_LIMIT` は **未使用**（`can_spend` のみ）
- `test_mock_patterns.test_costguard_blocks_llm` でブロック時スキップを検証済み

## エラーハンドリング

| 障害パターン | 処理 | 評価 |
|---|---|---|
| IMAP 接続失敗 | `ConnectionError` catch → スクリプト終了 | 良好 |
| ファイル破損 / 形式不一致 | `parse_file` が例外 catch → `None` → error カウント・継続 | 部分対応 |
| パスワード保護 Excel/PDF | 専用分岐なし。openpyxl/pdfplumber の汎用例外 → 同上 | **要改善** |
| 巨大ファイル | 添付サイズ上限なし（メモリに全読み込み）。LLM 入力は 8000 文字で truncate | **要改善**（メモリ） |
| テキスト短すぎ | 添付 200 文字未満 / シート 50 文字未満 → error | 良好 |
| スプレッドシート ログイン必要 | `login_required` → skip | 良好 |
| Playwright 未インストール | `status: error` → error | 良好 |
| Claude API / JSON 失敗 | 空リスト or unknown → error/skip | 部分対応 |
| Notion 登録失敗 | 最大 2 回リトライ（2 秒 sleep） | 良好 |
| 1 メール内の部分失敗 | 他の添付/URL は継続。UID は **常に処理済み記録** | **注意** — 失敗分の再処理不可 |

## パターン間の競合（添付 + URL 両方ある場合）

`importer.main()` のループ内で **独立に両方実行**（`SPEC.md` 記載どおり）:

1. `attachments` があれば `process_attachments()`（パターン A）
2. `sheet_urls` があれば `process_sheet_urls()`（パターン B/C）
3. `project_sheet_urls` があれば `process_sheet_urls_projects()`（未配線）

- 排他制御なし。同一メールから人員が二重登録される可能性あり（添付スキルシート + シート URL が同一人物の場合）
- 処理順: 添付 → 人員 URL → 案件 URL（後者は現状未到達）

## テスト結果

| コマンド | 結果 |
|---|---|
| `python -m pytest ses_work/mail_attachment_importer/tests/ -v` | **0 tests** — `tests/` ディレクトリ不存在 |
| `python test_mock_patterns.py`（実ディレクトリ直下） | **6/6 OK**（0.86s） |

**test_mock_patterns.py 内訳**

| テスト | 内容 | 結果 |
|---|---|---|
| `test_pattern_a_attachment` | 添付 → engineer 抽出 → Notion 登録 | pass |
| `test_pattern_b_single_sheet` | 単一 URL → 1 名登録 | pass |
| `test_pattern_c_multi_sheet` | 単一 URL → 3 名登録 | pass |
| `test_sheet_login_required_skipped` | ログイン必要シート skip | pass |
| `test_notion_upsert_by_name_and_affiliation` | 名前+所属検索 | pass |
| `test_costguard_blocks_llm` | CostGuard 上限時 LLM スキップ | pass |

**その他テストファイル**（調査指示の pytest 対象外）

- `test_integration.py` / `test_quick.py` — IMAP・Claude API 等の実接続が必要
- `test_imap.py` / `test_fetcher.py` — 手動確認用

## 推奨アクション

- [ ] `tests/` ディレクトリを作成し `test_mock_patterns.py` を pytest 収集可能に移行（または TASKS/調査手順のパスを修正）
- [ ] `.xls` は `xlrd` 等の別パーサー追加、`.doc` は変換または対象外明示で `SUPPORTED_EXTS` から除外
- [ ] `mail_fetcher.py` に `project_sheet_urls` 抽出ロジックを実装するか、`importer.py` のデッドコードを削除して仕様を統一
- [ ] 添付ファイルの MIME type / マジックバイト検証を追加し、拡張子不一致を早期検出
- [ ] 添付サイズ上限（例: 10MB）とパスワード保護ファイルの明示エラーメッセージを追加
- [ ] 1 メールに添付+URL 両方ある場合の重複登録防止（氏名ベース dedup または処理優先順位の定義）
- [ ] 部分失敗時の UID 処理済み記録ポリシーを見直し（全件成功時のみ mark_processed 等）
- [ ] `ai_extractor` に `reserve()` フェーズ制限を導入し、日次呼び出し回数を他モジュールと統一管理


---
R12_freee_invoice.md
---

# R12: freee請求書自動化 調査
調査日: 2026-06-18

## 結論（1行）
本番経路は `freee_invoice_v2.py` + `sheets_reader.py` で契約先別計算・源泉・支払サイト・GL月番号・/iv API は概ね正しいが、**FT階段粗利（75%/80%）未実装**・**`freee_invoice_monthly.py` が並行稼働（承認ゲートなし・60日バケット誤り・GL月番号なし）**・**Sheets読取の例外未捕捉**が残存リスク。

## 計算ロジック検証

**データフロー:** `sheets_reader.load_active_entries()` → 請求額 `seikyu` 計算 → `freee_invoice_v2.group_entries()` → `build_lines()` / `build_payload()` → POST `/iv/invoices`

**粗利:** `profit = tanka - shiire`（案件単価 − 仕入単価）。FT/GL は `profit <= 0` でスキップ。TERRA は粗利チェックなし。

| 契約先 | 粗利率 | 源泉徴収 | 支払サイト | 実装OK? |
|---|---|---|---|---|
| TERRA（BP通常） | 粗利×80% | 税抜×10.21%（行`withholding=True` + 見積`sub*1021/10000`） | Sheet「支払サイト」→30/45/60日バケット | ○ |
| TERRA（TERRA折半） | 粗利×50% | 同上 | 同上 | ○ |
| TERRA（岡本折半） | 粗利×80% | 同上 | 同上 | ○ |
| TERRA（プロパー・直契約） | 15,000円固定・合算行 | 同上 | 同上 | ○ |
| TERRA（GL/FT経由プロパー） | 請求なし | — | — | ○（`case`列 or 名寄せで除外） |
| FT（通常・岡本折半） | 粗利×68% | なし | **常に45日**（`get_payment_bucket` L91-92） | △（階段75%/80%未実装） |
| FT（小坂折半） | 粗利×48% | なし | 常に45日 | ○ |
| GL | 粗利×60% | なし | Sheet or 個人フォールバック（30/45日） | ○ |

**実装箇所（主要）**

| 項目 | ファイル | 行 |
|---|---|---|
| 請求額計算（TERRA/FT/GL） | `sheets_reader.py` | `_terra_entry` L179-219, `_ft_entry` L222-243, `_gl_entry` L246-263 |
| 源泉フラグ | `freee_invoice_v2.py` | `build_lines` L147, L162/176; `estimate_total_amount` L100-109 |
| 支払サイトバケット | `freee_invoice_v2.py` | `get_payment_bucket` L90-97, `payment_date` L121-125 |
| GL月番号 | `sheets_reader.py` | `_gl_entry` L262: `f"{name}様{m}月稼働分"` |
| GL/FT経由TERRAプロパー除外 | `sheets_reader.py` | `_terra_entry` L181-182; `load_active_entries` L349-354 |

**FT階段粗利（68%→75%→80%）:** 事業ルールに記載あるが、コード上は `_ft_entry` が **一律 0.68** のみ。件数カウントや契約マスター列からの切替ロジックは存在しない。

**並行スクリプト `freee_invoice_monthly.py`（`run_monthly_invoice.bat`）との差分**

| 項目 | v2 | monthly |
|---|---|---|
| データ取得 | `sheets_reader.load_active_entries`（稼働確定列・契約期間） | 独自 `load_people`（稼働中/月末終了のみ） |
| 件名 | `2026年7月分請求書` | `7月分請求書`（年なし） |
| 60日サイト | `return "60"` | `return "46"`（**バグ**: L102） |
| GL月番号 | あり | なし（`{name}様稼働分`） |
| `FREEE_WRITE_APPROVED` | 必須 | **なし** |
| `unit` | `""`（空欄） | `"式"` |

## freee API呼び出し

| 項目 | 仕様 | 実装 | OK? |
|---|---|---|---|
| 作成エンドポイント | POST `/iv/invoices` | `requests.post(f"{FREEE_BASE_INV}/invoices", ...)` L316 | ○ |
| 旧API廃止 | `/api/1/invoices` → 404 | 会計APIは取引先のみ（L202-217） | ○ |
| `company_id` | body トップレベル | `build_payload` L185 | ○ |
| `template_id` | 3323260 | L187 | ○ |
| `sending_status` | `unsent` | L196 | ○ |
| `unit_price` | 文字列型 | `str(person["seikyu"])` L173 | ○ |
| `unit` | 調査指示: 1文字以上（例: 式） | v2: `LINE_UNIT = ""` L50 | △（渋沢レビューは空欄を期待、`unit_check` L336-337） |
| 必須キー | `tax_fraction`, `withholding_tax_entry_method`, `partner_title` | L193-195（FIX済み） | ○ |
| 冪等性 | 重複防止 | `fetch_existing_invoice_keys` + `fetch_existing_invoice_triples` L401-411 | ○ |

**GET一覧も `/iv/invoices`:** 重複チェック・`shibusawa/invoice_review.py` の取得ともに `https://api.freee.co.jp/iv/invoices` を使用。

## 契約マスター（Google Sheets）取得

| 項目 | 内容 |
|---|---|
| SS ID | `1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI`（`sheets_reader.py` L27） |
| 認証 | `google_credentials.json` + gspread |
| シート | `TERRA` / `フラップテック` / `グレイスライン` |
| フィルタ | ステータス「稼働中」、契約期間内、`{年}年{月}月_稼働確定` 列（あれば TRUE 必須） |
| 列検索 | ヘッダー動的検索: 契約開始日・終了日・参画時期・期間・支払サイト |

## エラーハンドリング

| 障害 | 挙動 | 評価 |
|---|---|---|
| Sheets読取失敗 | `load_active_entries()` 内で未捕捉 → **プロセス全体クラッシュ** | △ |
| GET /iv/invoices 失敗（冪等） | `existing_keys`/`triples` が `None` → **全処理中止**（L402-410） | ○（安全側） |
| POST 失敗 | `NG` ログ出力、他グループは継続（L321-322） | ○ |
| 三重キー重複 | `DuplicateInvoiceError` → LINE通知松野（L426-430） | ○ |
| 支払サイト未入力（TERRA） | スキップ + LINE警告（`sheets_reader` L355-358） | ○ |

## 安全装置（確定防止）

| 装置 | 実装 | OK? |
|---|---|---|
| デフォルト dry-run | `dry_run = not args.execute`（v2 L465） | ○ |
| 実POST承認ゲート | `FREEE_WRITE_APPROVED=1` 必須（v2 L325-331, workflow L22-28） | ○（**monthly は未実装**） |
| 送信防止 | `sending_status: "unsent"`。POSTに `invoice_status` なし（draft相当） | ○ |
| 渋沢レビュー | `invoice_workflow.py` → `shibusawa/invoice_review.py`（draft-only、確定文言禁止 L75-81） | ○ |
| 手動確定後の送信 | `invoice_sender.py` は `confirmed/approved` のみ対象、デフォルト `--dry-run` | ○ |
| 二重請求防止 | partner×支払日 + partner×支払日×合計の二段チェック | ○ |

**注意:** `run_invoice.bat` は `freee_invoice_v2.py --execute` を直接呼ぶが、Python側で `FREEE_WRITE_APPROVED` 未設定時は `RuntimeError` で停止する。`run_monthly_invoice.bat` は **承認ゲートなし** で POST 可能。

## 推奨アクション

- [ ] **`freee_invoice_monthly.py` の退役または v2 への統合** — 承認ゲート・60日バケット・GL月番号・件名形式の不整合を解消
- [ ] **FT階段粗利（75%/80%）の実装方針確定** — 契約マスター列 or 稼働件数カウンタを SSoT に配線（現状は一律68%）
- [ ] **`load_active_entries()` 呼び出しに try/except を追加** — Sheets障害時にクラッシュせず松野LINE通知＋処理中止
- [ ] **`unit` 欄の方針統一** — freee API要件（1文字以上）と渋沢 `unit_check`（空欄期待）のどちらを正とするか決定
- [ ] **`run_monthly_invoice.bat` に `FREEE_WRITE_APPROVED=1` チェックを追加**、またはタスク登録を `invoice_workflow.py` 経由に一本化
- [ ] **TERRA BP の粗利≤0 チェック追加検討** — FT/GLのみ検証しており、異常データで請求0/マイナス行が出る余地あり


---
R13_line_bridge.md
---

# R13: LINE bridge 調査
調査日: 2026-06-18

## 結論（1行）
振り分け・キュー登録・5分cronの骨格は動くが、`handle_router_message` 未配線・引き継ぎ(jobz)タスクのワーカー対象外・push上限150のreply-only未実装・quota取得失敗時のpush試行・Scheduler二重実行時の競合が主要リスク。

## 振り分けロジック
| カテゴリ | 判定条件 | 漏れリスク |
|---|---|---|
| **即時（immediate）** | ①イニシャル+地名（`_INITIAL_PLACE_RE`）②`/` 始まり ③`IMMEDIATE_WORDS` 部分一致（「今日の案件」「進捗」「案件」「人材」等）④80文字以上 | **中**: 80字以上の非マッチング指示は無条件で即時系へ。`IMMEDIATE_WORDS` の「進捗」部分一致により「作業進捗」等も即時pass（後段 webhook の substring ハンドラに依存） |
| **営業重作業（sales）** | `SALES_HEAVY_WORDS` 部分一致（重作業/深掘り/提案文/評価表/意向確認文/面談調整）→ assignee=girard | **低**: 経理・開発キーワードより後段のため、複合文は他カテゴリ優先 |
| **経理（accounting）** | `ACCOUNTING_WORDS` 部分一致（請求/入金/契約マスター/freee等）→ shibusawa | **低**: `classify_route` 内で開発・営業より**先**に判定 |
| **開発（development）** | `DEVELOPMENT_WORDS` 部分一致 → codex/cursor。enqueue 時 `状態=blocked`（自動処理対象外） | **低**: 意図的にワーカー非実行 |
| **要確認（ambiguous）** | 上記いずれにも該当せず **80字未満** → 1問確認（1/2/3/4）→ 600秒TTL | **中**: 確認replyが `ROUTE_CHOICES` 外なら「判定できないためキュー未登録」で終了（最大1往復）。`immediate` 選択時は元文を即時系へ委譲 |
| **引き継ぎ（research/jobz）** | `_HANDOFF_MARKERS`（■/【/】/最優先/未完了）の**いずれか**を含む → `_HANDOFF_SECTION_RE` で ■セクション抽出 | **高**: マーカーだけ（【】のみ等）で `_extract_handoff_tasks` が空なら **None 返却→通常振り分けへ**。■見出し形式でない箇条書きは登録されない |
| **タスク回答** | `^#(T\d+)\s+(.+)$` 完全一致 | **低** |
| **非松野ユーザー** | `user_id != MATSUNO_USER_ID` → `action=pass` | 設計通り（既存 webhook 処理へ） |

**優先順位（`classify_route`）**: イニシャル/`/` → 経理 → 開発 → 営業重 → 即時KW → 80字以上 → ambiguous

**「進捗」コマンド（完全一致）** — `handle_router_message`（`line_bridge.py:892-908`）:
| 入力 | 動作 |
|---|---|
| `作業進捗` | `build_queue_progress(limit=10)` |
| `進捗` | 3種類の案内メッセージ |
| `案件進捗` / `人員進捗` | 「準備中」 |
| `確認済み` | human_review_items クリア |

⚠️ **配線ギャップ**: 本番 `webhook_server.py` は `route_line_message` を直接呼び **`handle_router_message` は未使用**。進捗系は L1899 の `"進捗" in text and len<=10`（部分一致）で処理され、案件DB進捗 + AIキュー進捗を返す。完全一致仕様と実挙動が不一致（例: 「進捗どう」も substring で反応、`handle_router_message` テスト期待とは逆）。

## 引き継ぎパーサー
- **■セクション正規表現**（B方式）:
  - 見出し: `■\s*(?:最優先|未完了[・･]?続きが必要なもの|次チャットで最初にやること)`（`_HANDOFF_SECTION_RE`）
  - 箇条書き: `^\s*(?:[-－ー•·]|・|\d+[.)．、])\s*(.+?)\s*$`（`_HANDOFF_BULLET_RE`）
- **検出マーカー**: `("■", "【", "】", "最優先", "未完了")` — 【】1文字でも handoff 経路に入る
- **フォールバック**: タスク0件 → `None`（サイレント）。通常 `classify_route` へ。登録成功時 reply「N件をキューに登録しました」
- **Notion登録**: `enqueue_task()` → `POST https://api.notion.com/v1/pages`（DB=`NOTION_AI_QUEUE_DB_ID`、デフォルト `37a450ff-...`）。route=`research`, assignee=`jobz`, 状態=`queued`
- **重大ギャップ**: `_query_queued()` は **girard / shibusawa のみ**取得（L940-968）。引き継ぎ jobz タスクは **キューに積まれるが `pickup_and_run` では処理されない**

## ThreadPoolExecutor安全性
- **max_workers=5**: `line_bridge/SPEC.md` の並列設計（Cloud Run `--max-instances=5`, `--concurrency=1`）に対応。1 cron あたり最大5タスク同時 LLM 実行
- **負荷**: デフォルト `LINE_BRIDGE_PICKUP_LIMIT=50` 件を query 後、最大5並列。各タスク `guarded_anthropic_call` timeout=90s → 最悪 ~450s 相当だが gunicorn `--timeout 120` で Cloud Run 側が先に切れる可能性
- **スレッド内例外**: `_process_single_task` が全例外 catch → 当該タスクのみ `blocked`、他スレッド継続。**良好**
- **競合防止（同一タスク）**: `queued→running` PATCH 後 GET で status 確認。Notion に原子 CAS がないため **Scheduler 二重起動時に同一タスク二重処理の余地あり**
- **タイムアウト**: `future.result()` に **timeout なし**。1スレッド hang で worker エンドポイント全体がブロックしうる
- **CostGuard**: スレッド間は `threading.Lock()` で日次/月次 USD 管理。上限超過は当該タスクのみ `CostLimitError→blocked`

## push上限管理
| 項目 | 実装 | 評価 |
|---|---|---|
| **`push_or_log()`** | `_line_push_remaining()` で quota/consumption API 取得 → `remaining != 0` なら push → 失敗時 Notion に `push_fail_*` または既存 task の結果リンク追記 | **部分対応** |
| **残通数取得** | LINE API `GET /v2/bot/message/quota` + `/quota/consumption`。エラー時 **-1** | API ベース（ローカルカウンターなし） |
| **月次リセット** | LINE 側の公式 quota リセットに依存。コード側リセット処理なし | 設計通り |
| **150通 reply-only** | `INFRA_SUMMARY_20260610.md` に記載あるが **`push_or_log` / `webhook_server.push_message` いずれにも未実装**。残0のときのみ push スキップ | **未実装（仕様とコード乖離）** |
| **`remaining == -1` 時** | `remaining != 0` が真のため **push を試行**（quota 不明でも送信） | **バグ** |
| **`consume_completion_push_budget()`** | 当月完了タスク数 vs `LINE_BRIDGE_PUSH_MONTHLY_LIMIT`(default 20) を Notion カウント。`webhook_server` に import されるが **呼び出し箇所なし**（2026-06-15 完了push廃止後の死コード） |
| **webhook 直 push** | `push_message()` は quota チェックなしで Messaging API push（マッチング複数チャンク等） | reply 無制限だが **push 枠を直接消費** |
| **利用箇所** | mail_pipeline, sheets_reader, freee_invoice_v2, metrics_daily_summary 等が `push_or_log` 使用 | gate_checker は TASKS.md 上は未配線 |

## Cloud Scheduler連携
- **エンドポイント**: `POST /line-bridge/worker`（`webhook_server.py:2445`）。併せて `POST /line-bridge/expire`（失効専用）
- **スケジュール**: `*/5 * * * *`（ジョブ名 `line-bridge-worker-cron`, asia-northeast1）— `line_bridge/SPEC.md` 記載
- **認証**: ヘッダー `X-Line-Bridge-Token` == env `LINE_BRIDGE_CRON_TOKEN`（空なら **403**）。`cron_authorized()` / `worker_authorized()` 同一
- **処理内容**: `pickup_and_run()` →（push は 2026-06-15 廃止、`pushed=0` 固定）→ `expire_finished()` 同梱
- **二重実行防止**: **なし**（分散ロック・idempotency key なし）。Cloud Run `--concurrency=1` はインスタンス内のみ。5分 overlap や手動 trigger 併用時は queued タスクの二重 pickup リスク
- **監視**: `line_bridge/check_worker_health.py` が worker POST + Notion キュー監視（running 30分 stale 検知）。異常時は **push 直叩き**（`push_or_log` 非経由）

## 推奨アクション
- [ ] **P0**: `webhook_server.process_message` を `handle_router_message` 経由に統一し、進捗コマンドの完全一致/substring 二重定義を解消
- [ ] **P0**: `push_or_log` を `remaining > 0` のみ push に修正（`-1` は Notion ログのみ）。残 **≤150** で reply-only フラグを実装し `push_message` 直叩き箇所にも適用
- [ ] **P0**: 引き継ぎ(jobz/research)タスクのワーカー方針を決定 — `_query_queued` 拡張 or jobz 専用処理 or 登録時に blocked+手動明示
- [ ] **P1**: Scheduler 二重実行対策 — Notion `queued→running` を条件付き更新相当（取得直後再query + page_id 単位ロック）または Cloud Scheduler `attemptDeadline` / 実行中スキップ
- [ ] **P1**: `pickup_and_run` の `future.result(timeout=...)` と Cloud Run timeout の整合（120s 内に収める pickup limit 見直し）
- [ ] **P1**: 引き継ぎパーサー — マーカー検出と ■セクション不一致時に「形式エラー」を reply（サイレント fallthrough 廃止）
- [ ] **P2**: 未使用 `consume_completion_push_budget` import を削除 or 再配線の方針決定
- [ ] **P2**: `check_worker_health.send_line_alert` を `push_or_log` 経由に変更（quota 管理の一元化）
- [ ] **P2**: gate_checker の残80/150通閾値を `push_or_log` オプション引数として実装（現状 TASKS.md のみ）


---
R14_cost_guard.md
---

# R14: cost_guard_v2 調査
調査日: 2026-06-18

## 結論（1行）
cost_guard_v2（`allowed()`/`finalize()` + SQLite SSoT）は3装置・予約制限・claim dedup・原子finalizeが実装済みで113/116テスト合格；残課題はUTC/JST日付境界の不整合、WAL未設定、legacy `CostGuard` クラス欠落、および調査指示の「装置3=Notion自動起票」と実装（重複起票防止）の定義差。

## 3装置の実装状況
| 装置 | 機能 | 実装状態 | 問題点 |
|---|---|---|---|
| 装置1 | フェーズ別モデル選択 + DAILY_CALL_LIMIT（予約方式）+ グローバル予算 `$8/日・$140/月` | 実装済み（`common/model_selector.py` + `common/ledger.reserve()` + `cost_guard.allowed()` Step 1/6/7） | 日付キーが UTC（ledger）vs JST（Layer2 `get_costs()`）で日次境界がずれる可能性 |
| 装置2 | フェーズ別単発コスト閾値（light `$0.025` / medium `$0.10` / heavy `$0.15`） | 実装済み（`cost_guard._phase_threshold()` → Step 3、超過時 `exit_code=1`） | `.env` の `PHASE_THRESHOLD_*` 未設定時はコード内デフォルト値を使用 |
| 装置3 | 重複起票防止（claim方式 + `target_id` 必須マップ） | 実装済み（`common/dedup.claim_dedup()` + SQLite UNIQUE、`config/dedup_target_required.json`） | 調査指示の「auto Notion ticket creation」とは別物（Notion起票は `tests/test_notion_register.py` 等で独立）；通知は `common/notifier.py`（LINE）のみ |

**補足（2層アーキテクチャ）**

- **Layer1（v2 per-call）**: `cost_guard.allowed()` / `finalize()` — 各 LLM 呼び出し前後
- **Layer2（緊急停止）**: `cost_guard.main()` — `$20/日・$300/月` で Windows タスク停止 + Cloud Run `LLM_KILL=1`

## DAILY_CALL_LIMIT

### 仕様
- デフォルト: `DAILY_CALL_LIMIT_DEFAULT=30`（`.env` / `common/ledger._call_limit()`）
- フェーズ別オーバーライド: `DAILY_CALL_LIMIT_<PHASE>`（例: `DAILY_CALL_LIMIT_IMPLEMENTATION=10`）
- 判定式: `consumed + reserved >= limit` なら予約不可

### reservation-based locking の実装
`common/ledger.reserve(phase)`（`BEGIN IMMEDIATE` 内）:

1. `phase_calls` から `(date, phase)` の `reserved` / `consumed` を読む
2. 在庫があれば `reserved += 1` し `reservations` に UUID 行を INSERT
3. 上限到達なら `None` を返す（ロールバック）

### 予約→消費→解放ライフサイクル

| イベント | `reserved` | `consumed` | `reservations.finalized` |
|---|---|---|---|
| `reserve()` 成功 | +1 | 変化なし | 0 |
| `finalize(success=True)` → `_record_in_tx` | -1（MAX(0)） | +1 | 1 |
| `finalize(transient)` → `_release_in_tx` | -1（MAX(0)） | 変化なし | 1 |
| `allowed()` で budget 超過 cleanup | -1 | 変化なし | 1 |

- **重複呼び出し**（`skipped_duplicate`）: claim が失敗するため `reserve()` まで到達せず、**daily call を消費しない**（`tests/test_duplicate_does_not_consume_daily_call.py` で検証）

### デッドロックの可能性
- SQLite 単一ファイル + 全更新が `BEGIN IMMEDIATE` — 伝統的デッドロック（循環待ち）は**低い**
- 競合時は `OperationalError: database is locked` → `error_internal` / `detail=lock_timeout` / `exit_code=2`（timeout **5秒**、`SQLITE_TIMEOUT_SEC`）
- 予約取得後に後段失敗した場合、claim/reservation の rollback パスが実装済み（budget 超過・lock_timeout 等）
- **リスク**: 5秒 timeout 超過時に呼び出し側が `finalize()` 未実行だと `reserved` が一時的に残る（`finalized=0` の orphan reservation）。TTL による自動回収は未実装

## claim-based deduplication

### 重複検出方法
- `dedup_key = f"{date}:{block_type}:{phase}:{target_id}"`（UTC 日付、`common/dedup.compose_dedup_key()`）
- `claim_dedup()` が `INSERT OR FAIL INTO dedup_claims ... UNIQUE(dedup_key)` — 後着プロセスは `IntegrityError` → `claim_id=None` → `skipped_duplicate` / `exit_code=2`

### タイムウィンドウ
- デフォルト TTL: **3600秒（1時間）**（`.env: DEDUP_CLAIM_TTL_SEC`）
- 同一 `dedup_key` の再実行可否:
  - **confirmed=1, error=0/1**（成功/permanent）: TTL 内はブロック、confirmed レコードは purge しない
  - **confirmed=1, error=2**（transient release）: 即座に DELETE され再 claim 可能
  - **confirmed=0 かつ TTL 超過**: inline purge で DELETE され再 claim 可能

### finalize との連携
- success → `confirm_dedup(error=False)`
- permanent → `confirm_dedup(error=True)`（再試行不可）
- transient → `release_dedup`（`error=2` マーカー、再試行可）

## 並列制御

### 複数プロセス同時アクセス
- DB パス: `%LOCALAPPDATA%/ses_work_state/state.sqlite3`（OneDrive 外、`common/state_store.get_db_path()`）
- 全書き込み: `BEGIN IMMEDIATE` トランザクション（`reserve`, `claim_dedup`, `finalize`, `log_event`）
- レーステスト: `tests/test_call_limit_race.py`, `tests/test_dedup_claim_race.py`

### WALモード / busy_timeout
| 項目 | 実装値 | 備考 |
|---|---|---|
| journal_mode | **delete**（デフォルト） | コード内で `PRAGMA journal_mode=WAL` 未設定 |
| busy_timeout | **5000 ms** | `sqlite3.connect(..., timeout=5)` 経由 |
| ロック戦略 | BEGIN IMMEDIATE のみ | 読み取りは autocommit、書き込みは排他 |

WAL 未使用のため、書き込み競合時は reader/writer 双方がブロックされうる。5秒 timeout で `lock_timeout` に落ちる設計。

## cost_state.jsonとSQLiteの関係

| ストア | パス | 役割 | SSoT |
|---|---|---|---|
| SQLite `state.sqlite3` | `C:\Users\ma_py\AppData\Local\ses_work_state\state.sqlite3` | daily/monthly USD、phase_calls、reservations、dedup_claims、event_log | **正（v2.4 以降）** |
| `cost_state.json` | 同上ディレクトリ | v2.4 移行前の JSON ledger | **移行済み** → `cost_state.json.bak_v2.4`（2026-06-16 時点: daily=$0.03, monthly=$6.22） |
| `cost_guard_state.json` | OneDrive `ses_work/cost_guard_state.json` | Layer2 緊急停止フラグ（`stopped_today` 等） | Layer2 専用（コスト累計とは別） |
| `usage_tracker/cost_log.jsonl` | OneDrive 配下 | 監査用 append-only ログ | 参照用；ledger 読み取りエラー時は `can_spend` が True を返す（フェイルオープン） |

### 更新タイミング
- **SQLite**: `finalize()` 成功/permanent 時の `_record_in_tx()` で `daily_state` / `monthly_state` UPSERT
- **cost_log.jsonl**: `ledger.record()` / blocked 時の `_append_log()` で追記
- **cost_state.json**: 現行コードからは**書き込みなし**（`migrate_to_sqlite_v2.4.py` で一回移行のみ）

### 不整合リスク
1. **`cost_guard.get_costs()` の stale コメント** — 「cost_state.json を正とし」と記載あるが、実際は `ledger.daily_total()` / `monthly_total()`（SQLite）を `max()` 合成
2. **UTC vs JST** — ledger の date/month キーは UTC、Layer2 の cost_log 集計は JST 00:00。JST 09:00 前後で日次境界が Layer1/Layer2 で不一致になりうる
3. **`can_spend` 読み取りエラー時 True** — DB 破損/ロック時に予算ガードがスキップされる（意図的フェイルオープン）
4. **orphan reservation** — finalize 未到達 + lock_timeout 時に `reserved` が残存しうる

## 月次管理

### リセットタイミング
- **明示的リセット処理なし** — キー切り替え方式
- `monthly_state`: `_now_month()`（UTC `YYYY-MM`）が変わると新行 INSERT、旧月データは残存
- `phase_calls` / `daily_state`: UTC 日付キーで日次自動切替
- Layer2 `cost_guard_state.json`: `reset_state_if_needed()` で JST 日付/月変更時に `stopped_today` / `stopped_monthly` フラグをリセット

### リセット中の保護
- 月跨ぎ瞬間: 新 `month` キーは `monthly_usd=0` から開始 → 一時的に予算に余裕ができる（意図通り）
- 同時 API 呼び出し: `BEGIN IMMEDIATE` で serialize — リセット「処理中」という特殊状態はなく、新旧 month キーへの INSERT/UPDATE が競合するだけ
- **注意**: UTC 月初 00:00 と JST 月初 00:00 が9時間ずれる

## テスト結果

```
pytest tests/ -q  →  113 passed, 3 failed, 2 warnings（実行日: 2026-06-18）
```

| 区分 | 件数 | 内容 |
|---|---|---|
| cost_guard コア（dedup/reserve/finalize/exit_code 等） | **113 合格** | `tests/test_*` のうち cost_guard 関連は全 PASS |
| 失敗 3件 | `tests/test_mail_pipeline_bc.py` | cost_guard 無関係（削除済み関数 `_parse_imap_internaldate`, `notion_register_engineer`, `maybe_save_processed_id` 参照） |
| 警告 2件 | race テスト | `@pytest.mark.timeout` 未登録 |

**116テスト**: `tests/` ディレクトリ合計 116 件。指示書の「116 passing」は mail_pipeline_bc 3件を除く **113/113 cost_guard 関連 PASS** と解釈するのが正確。

### 主要テストファイル（cost_guard v2）
- `test_call_limit.py`, `test_call_limit_race.py` — DAILY_CALL_LIMIT 予約
- `test_dedup_claim*.py` — claim/TTL/race/transient
- `test_finalize_*.py` — 原子性・冪等・state_mismatch
- `test_exit_code2.py`, `test_judge_order.py`, `test_phase_threshold.py`
- `test_duplicate_does_not_consume_daily_call.py`

## exit code 2（cost/rate limit skip）の使われ方

### SPEC 定義（`cost_guard.Reasons` + `Decision.exit_code`）

| exit_code | reason 例 | 意味 | 呼び出し側の期待動作 |
|---|---|---|---|
| **0** | `ok` | 許可 | LLM 実行 → `finalize()` |
| **1** | `stopped_budget`, `stopped_call_limit`, `stopped_phase_threshold` | 停止（当日/入力変更まで不可） | スキップまたはエラー扱い |
| **2** | `skipped_duplicate`, `error_transient_*`, `error_*`, `error_internal` | スキップ（リトライ可/不要） | **正常スキップ**として処理継続 |

### 実装箇所
- `cost_guard.allowed()` — 各 Step の失敗時に `Decision.exit_code` を設定
- `common/exit_handler.ExitCode2` — exit 2 を例外として伝播
- `matching_v3/skill_judge.py`:
  - `exit_code == 2` → `raise ExitCode2`（スキップ）
  - `exit_code == 1` → `raise RuntimeError`（ブロック）
- `common/exit_handler.run_with_skip()` — `ExitCode2` / `SystemExit(2)` をキャッチして `None` 返却

### LLM_KILL=1
- Layer2 `cost_guard.main()` が `$20/日` or `$300/月` 到達時に Cloud Run env + Windows タスク DISABLE
- per-call の exit code 2 とは別系統（インフラレベル即時停止）

## 推奨アクション
- [ ] **UTC/JST 日付キー統一** — `ledger._now_date()` / `_now_month()` を JST に揃えるか、SPEC に UTC 運用を明記
- [ ] **SQLite WAL 有効化検討** — `init_schema()` 後に `PRAGMA journal_mode=WAL` + reader 競合低減
- [ ] **orphan reservation 回収** — `finalized=0` かつ `created_at` 超過分を定期 purge（または stale reservation TTL）
- [ ] **legacy `CostGuard` 整理** — ルート `cost_guard.py` から `CostGuard` クラスが削除済みだが `matching_v3/matching_v3.py` が `from cost_guard import CostGuard` を参照（import 失敗リスク）。`matching_v3/cost_guard.py` への import 修正または re-export
- [ ] **stale コメント修正** — `cost_guard.get_costs()` L165「cost_state.json を正とし」→ SQLite ledger に更新
- [ ] **`test_mail_pipeline_bc.py` 3件修正** — 116/116 PASS を回復（cost_guard とは独立）
- [ ] **憲法/ドキュメント更新** — `ジョブズ行動憲法v1.md` の「cost_state.json 正本」記述を SQLite SSoT に更新


---
R15_gate_checker.md
---

# R15: gate_checker 調査
調査日: 2026-06-18

## 結論（1行）
実装は v1.0 系（全フェーズ GPT-4o + Gemini 2.0 Flash 固定・日次10回）のまま残存しており、SPEC v2.2 のフェーズ別モデルルーティング・装置2・装置3は未実装；`needs_human_review()` は3層構造を持つが層3は別API呼び出しではなくレビュー本文の `HUMAN_REVIEW:` 行依存で、仕様キーワードとの乖離と層1/2の過検知リスクが残る。

## メイン処理フロー（`gate_check.py`）

```
main() → run_gate_check(phase, file, dir, tasks)
  ├─ phase 検証（6フェーズ）
  ├─ check_daily_limit()  … 超過時 save_result + return 2（装置3なし）
  ├─ パス解決 / .env 読込 / OPENAI_API_KEY 必須
  ├─ load_phase_prompt(phase)  … prompts/{phase}.txt 優先
  ├─ build_user_prompt()  … 対象ファイル/ディレクトリ + SPEC/CLAUDE/TASKS
  ├─ run_dual_review()  … agreement_checker（GPT-4o ∥ Gemini 並列）
  ├─ increment_daily_counter()  … API成功後のみ
  ├─ resolve_human_review(verdict, phase, review_text)
  ├─ verdict==OK
  │    ├─ human_review → send_line_notification（直接 LINE API）
  │    └─ save_result → return 0
  └─ verdict==NG
       ├─ human_review → send_line_notification
       ├─ else → run_wall_hitting()（subprocess）
       ├─ save_result
       ├─ update_tasks_on_ng()  … ゲート①/②フラグを [!]
       └─ return 1
```

**デッドコード**: `call_gpt4o()`（`gate_check.py:379-427`）は CostGuard 付きだが `run_gate_check` からは未呼び出し。実際の LLM 経路は `agreement_checker.run_dual_review()` のみ。

## フェーズ別モデルルーティング
| フェーズ | SPEC v2.2 設定モデル | 実装確認 |
|---|---|---|
| research | gpt-5.4-nano | **未適用** — `agreement_checker` が全フェーズ共通で `gpt-4o`（`call_gpt4o_simple`）+ `gemini-2.0-flash`（`GEMINI_URL`） |
| requirements | gpt-5.4-mini | 同上 |
| design | gpt-5.4 | 同上 |
| pre_impl | gpt-5.4 | 同上 |
| implementation | gpt-5.3-codex | 同上 |
| test | gpt-5.4-mini | 同上 |

**実装詳細**
- `phase_models.py` / `resolve_model()` は **存在しない**（`TASKS.md` Phase 1 は全項目未完了）
- `REVIEW_MODEL = "gpt-4o"` は `gate_check.py:38` に残存するが、本番経路では未使用
- 結果 JSON の `model` フィールドは常に `"gpt-4o+gemini"`（フェーズ非依存）
- `GATE_MODEL_{PHASE}` 等の .env 上書きは **未実装**
- `OpenAI.models.list()` による可用性チェック・fallback は **未実装**

## needs_human_review() 3層チェック
| 層 | 実装 | 網羅性 | リスク |
|---|---|---|---|
| 1. 完全一致キーワード | `gate_check.py:170-176` — 9語: 運用フロー, 仕様変更, データ削除, 本番DB, 契約, 岡本, コスト増, 仕様修正, 要件変更 | 調査指示・`cursor_workflow_rules.md` の例（「費用が発生」「岡本に連絡」「契約変更」）と **不一致**。「費用が発生」「契約変更」は未登録 | **FN**: 上記フレーズのみで書かれたレビューは層1をすり抜ける |
| 2. 類義語辞書 | `gate_check.py:178-211` — 7カテゴリ・計40語超（契約→取引先/請求/TERRA等、コスト増→料金増加/API料金等） | 「コスト」単体は未登録（「コスト増」カテゴリの類義のみ）。`truncate`/`drop` 等の英語語もヒット | **FP**: レビュー本文に「請求」「API料金」等が出ると層1/2で即 True（`test_human_review_override.py` で GO+HUMAN_REVIEW:NO による抑制を確認済み） |
| 3. GPT自己判定 | **別API呼び出しなし**。レビュープロンプト末尾で `HUMAN_REVIEW: YES/NO` 出力を指示（`prompts/*.txt`）し、本文に `HUMAN_REVIEW: YES` があれば True（`gate_check.py:213-214`） | `resolve_human_review()`（`gate_check.py:219-224`）で **verdict==OK かつ HUMAN_REVIEW:NO のとき層1/2を上書きして False** | **FN**: 層1/2未ヒットかつモデルが `HUMAN_REVIEW:` 行を省略、または誤って NO とした場合は人間確認なしで通過。**FN**: NG+HUMAN_REVIEW:NO は wall_hitting 経路（松野確認なし） |
| （補足） | `_phase` 引数は **未使用**（フェーズ別ルールなし） | — | research 等でプロンプトに HUMAN_REVIEW 指示がない経路は層3が機能しないが、現状は全6フェーズの `prompts/*.txt` に指示あり |

**層3プロンプト例**（`prompts/implementation.txt:14-18`）:
```
HUMAN_REVIEW: YES  ← 運用・仕様・コスト・契約・本番データに影響する場合
HUMAN_REVIEW: NO   ← 技術的な修正のみで影響範囲が実装内部に閉じる場合
判断に迷う場合は HUMAN_REVIEW: YES にしてください。
```

**組み込みプロンプト（builtin）との差**: `gate_check.py` 内の `REQUIREMENTS_SYSTEM` 等（`prompts/` 不在時のフォールバック）には `HUMAN_REVIEW` 指示が **ない**。現状は `prompts/` ファイルが存在するため通常はファイル版が使われる。

## 装置2・装置3
| 装置 | SPEC v2.2 | 実装確認 |
|---|---|---|
| **装置2** 単発コスト警告 | クラス別閾値: 軽 $0.025 / 中 $0.10 / 重 $0.15。超過時 `cost_alerts.jsonl` + LINE（同日同phase同class 1回） | **未実装** — `cost_calc.py` なし、`results/cost_alerts.jsonl` なし。`push_or_log` 未使用 |
| **装置3** CostGuard停止時 Notion 起票 | `handle_costguard_blocked()` → AI作業キュー DB（`37a450ff-...`）に `gate_costguard_{block_type}_{phase}_{yyyymmdd}`、LINE 並行、重複抑制 | **未実装** — `costguard_handler.py` なし、`costguard_blocks*.jsonl` なし |

**日次上限超過時の実際の挙動**（`gate_check.py:578-598`）:
- `DAILY_CALL_LIMIT = 10`（ハードコード。SPEC の 30 未適用）
- `verdict: LIMIT_EXCEEDED` で JSON 保存 → **return 2**
- Notion 起票なし / LINE なし / `handle_costguard_blocked` なし

**CostGuard 拒否時**（`agreement_checker.py:296-298`）:
- `can_spend(6000, 6000, "gpt-4o")` が False → `RuntimeError` → `gate_check.py` で ERROR ペイロード保存 → **return 1**（SPEC の exit 2 ではない）
- Notion 起票なし

## CostGuard自己適用
| 経路 | can_spend（事前） | record（事後） | 備考 |
|---|---|---|---|
| `agreement_checker.run_dual_review()` | **あり** — 1回のみ `can_spend(6000, 6000, "gpt-4o")` | GPT: 実トークン / Gemini: 固定 `3000/3000` | Gemini 分の事前見積もりは未個別チェック。ledger 記録モデル名 `gemini-2.5-flash` と実 API `gemini-2.0-flash` が **不一致** |
| `gate_check.call_gpt4o()` | あり（未使用デッドコード） | あり | — |
| `gate_check.send_line_notification()` | なし（LLM 不使用） | — | — |
| `run_wall_hitting()` | wall_hitting 内部で実施（本調査スコープ外だが SPEC も Week2 確認待ち） | — | NG かつ human_review=False 時に subprocess 起動 |

**ledger 上限**（`common/ledger.py`）: 日次 `COST_GUARD_DAILY_USD` デフォルト $8.0、月次 $140.0（.env 上書き可）

## エラーハンドリング
| エラー | 実装 | SPEC v2.2 との差 |
|---|---|---|
| GPT API 失敗 | `agreement_checker`: 429 は指数バックオフ最大3回。最終失敗は `ModelResult(ERROR)` → Gemini 単独 or 両方 ERROR で NG | 概ね一致 |
| Gemini API 失敗 | 429 は10秒待ち1回リトライ。ERROR 時 GPT 単独フォールバック（`judge()`） | 一致 |
| 判定パース失敗 | `parse_judgment()` → UNKNOWN/NG（保守的） | 一致 |
| CostGuard 拒否 | ERROR + exit 1 | SPEC は装置3 + exit 2 |
| 日次上限 | LIMIT_EXCEEDED + exit 2、通知・起票なし | 装置3 + exit 2 が未実装 |
| Notion API 失敗 | 該当コードなし（装置3未実装） | — |
| LINE 通知 | `send_line_notification()` が **直接** `api.line.me` に POST。429 リトライなし、失敗はログのみ | SPEC は `push_or_log` 経由（残通数確認・失敗時 Notion フォールバック）。月200通上限対応 **なし** |

## 推奨アクション
- [ ] **P0**: SPEC v2.2 Phase 1–2 を実装（`phase_models.py` / `cost_calc.py` / `costguard_handler.py` + `gate_check.py` 統合）。現状は設計のみ完了・コード未着手
- [ ] **P0**: `needs_human_review` 層1キーワードを運用仕様（「費用が発生」「岡本に連絡」「契約変更」）と同期し、「コスト」単体を類義語に追加
- [ ] **P1**: 層3の FN 対策 — `HUMAN_REVIEW:` 行が欠落した場合は保守的に True、または NG 時は常に human_review=True
- [ ] **P1**: `send_line_notification` を `line_webhook.line_bridge.push_or_log` に置換（月200通・失敗時 Notion フォールバック）
- [ ] **P1**: CostGuard 拒否時の exit code を 1→2 に変更し `handle_costguard_blocked` を接続
- [ ] **P2**: `call_gpt4o()` デッドコード削除または `run_dual_review` への CostGuard/モデルルーティング統合
- [ ] **P2**: Gemini ledger 記録モデル名（`gemini-2.5-flash`）と実 API（`gemini-2.0-flash`）の整合
- [ ] **P2**: builtin プロンプト（`REQUIREMENTS_SYSTEM` 等）にも `HUMAN_REVIEW` 指示を追加（prompts ファイル欠落時の安全網）
- [ ] **P2**: `DAILY_CALL_LIMIT` を `GATE_DAILY_CALL_LIMIT`（デフォルト30）に変更
