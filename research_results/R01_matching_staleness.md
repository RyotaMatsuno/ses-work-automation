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
