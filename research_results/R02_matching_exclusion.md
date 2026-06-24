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
