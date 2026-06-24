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
