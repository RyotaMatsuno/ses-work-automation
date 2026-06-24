# GPT壁打ち結果: 全システム調査優先順位付け
実行日: 2026-06-19
モデル: o4-mini (reasoning effort: medium)

以下、ご要望の５問について回答します。

――――――――――――――――  
Ｑ１．全20項目の優先度（P0／P1／P2）分類と理由  
――――――――――――――――  
P0（即対応必須．案件取りこぼし・大幅コスト超過・データ欠損直結）  
1. pipelineがCostGuard v2未統合  
　– get_today_cost_usd() fail‐openで制限外課金・コスト計上漏れ→予算超過リスク大  
2. Notion登録失敗でも再処理不可  
　– 案件データ永久ロスト→営業チャンス消失  
3. importer毎回exit 255クラッシュ  
　– メール登録途切れ→500件以上の案件流入を取りこぼし  
4. pipeline Batch APIにコスト記録なし  
　– classify_email_v2経路でコストカウントせず→月次集計大幅ズレ  
5. 語彙外必須スキル31件が自動パス→MATCH化  
　– 必須スキル不足案件を誤通知→営業タイムロス・顧客信頼低下  
6. soft-skill all-pass未実装  
　– ソフトスキル判定漏れ→案件ミスマッチ  
8. Notion 400フォールバックで全員マッチング対象  
　– 全エンジニア提案→ノイズ多発・工数無駄  
9. BTM/NBW案件がengineer判定→skip  
　– 有望案件を自動除外→売上機会損失  

P1（至急だが営業インフラ直撃度はP0より低い／中期対応可）  
7. 並行情報の当日確認チェック未実装  
　– ルール違反で古い案件提案の恐れ  
10. 尚可スキル＋粗利乖離チェック未配線  
　– 利益率管理ずれ→収益圧迫リスク  
12. SQLite WAL未設定  
　– DB障害／ロック増大リスク  
13. gate_checker v2.2未実装  
　– フェーズ管理漏れ→ワークフロー破綻  
14. LINE push残通数-1時にpush試行  
　– 通知エラー増加→重要通知取りこぼし  
15. freee_invoice_monthly.pyが承認ゲートなしで並行稼働  
　– 請求ミス・重複処理リスク  
16. FT階段粗利75%/80%未実装  
　– 利益計画ずれ  
18. スケジューラ二重共存  
　– 重複実行／デバッグ困難  
19. IMAP接続タイムアウト未設定・リトライなし  
　– メール取得タイムアウトで失敗多発  
20. UTC/JST日付境界不整合  
　– 日切りロジック誤動作  

P2（影響小／迂回策あり／後回し可）  
11. 備考フォールバックの結果待ちが2.0固定  
　– 日数分岐ロジック微調整のみ  
17. needs_human_review層1キーワード仕様不一致  
　– レビュー漏れ頻度低・運用フォロー可  

――――――――――――――――  
Ｑ２．P0各項目のCursor向け作業指示骨子  
――――――――――――――――  
以下は各Issueごとに「CLAUDE.md（背景・狙い）」「SPEC.md（API／ファイル修正要件）」「TASKS.md（具体タスク）」をまとめた骨子例です。

1. pipelineがCostGuard v2未統合  
 CLAUDE.md  
  - 現状：mail_pipelineバッチはCostGuard v2を経由せず、独自$2制限のみ。バックログ回復時に過剰課金。  
  - 目的：全経路でCostGuard v2を通し、月次APIコストを正確把握／制限超過防止  
 SPEC.md  
  - 対象：pipeline/mail_pipeline.py  
  - 追加：send_batch()内で CostGuardV2.track_batch(cost, id) 呼び出し  
  - 例外時 fail‐close モード（例外で停止／アラート）  
 TASKS.md  
  1. mail_pipeline.py を開く  
  2. get_today_cost_usd() 呼び出し箇所を CostGuardV2.get_cost() に置換  
  3. Batch API 実行前後で log_cost() → CostGuardV2.track_batch() 追加  
  4. 異常時 raise させるテストケース作成  

2. Notion登録失敗でも再処理不可  
 CLAUDE.md  
  - 現状：register_project()失敗後でも finally で processed_id を保存し、二度と再試行せずデータロスト  
  - 目的：429含む一時エラー時はリトライ／upsert ロジックを正しく利用  
 SPEC.md  
  - 対象：common/notion_register.py, batch/register_project.py  
  - ロジック：登録成功時のみ save_processed_id()。失敗時は例外伝播 or リトライ  
  - 429 は backoff + retry up to 3回。成功後 upsert。  
 TASKS.md  
  1. register_project() 内 finally ブロック削除  
  2. 成功フラグ判定後に save_processed_id()  
  3. common/notion_register.py の retry+upsert 部分を import＋利用  
  4. 異常シナリオをユニットテスト  

3. importer毎回exit 255クラッシュ  
 CLAUDE.md  
  - 現状：jobz_importerがログも出さず255で落ち、データ欠損  
  - 目的：例外捕捉＋詳細ログ出力で安定稼働  
 SPEC.md  
  - 対象：scripts/importer.py, Task Scheduler定義  
  - 追加：最上位で try/except Exception, ログ出力、リトライ or 警告メール  
  - IMAPタイムアウト（#19）緊急対応含める  
 TASKS.md  
  1. importer.py にログ基盤（structlog等）追加  
  2. main() を try/except で囲み traceback 出力  
  3. タイムアウト & retry ロジック追加（IMAP）  
  4. タスクスケジューラのログ保存先設定確認  

4. pipeline Batch APIにコスト記録なし  
 CLAUDE.md  
  - 現状：classify_email_v2 が直接API呼び出し、log_cost()をすり抜け  
  - 目的：全Batchクラス呼び出しに log_cost() を必須化  
 SPEC.md  
  - 対象：pipeline/classify_email_v2.py  
  - 改修：バッチ呼び出し wrapper 追加。内部で log_cost(batch_size * unit_cost)  
  - テスト：モックAPIでコスト集計検証  
 TASKS.md  
  1. classify_email_v2.py で API呼び出し箇所を wrapper 関数に差し替え  
  2. wrapper に log_cost 呼び出し実装  
  3. 単体テスト追加  

5. 語彙外必須スキルsilent pass→MATCH化  
 CLAUDE.md  
  - …（略）  
 SPEC.md  
  - 対象：matcher/skill_normalizer.py  
  - 未正規化語彙は “UNKNOWN” タグ付与し、必須チェックに含める  
 TASKS.md  
  1. 正規化失敗時に warning → リスト帰却  
  2. 必須スキル存在確認ロジック修正  

6. soft-skill all-pass未実装  
 CLAUDE.md  
  - …  
 SPEC.md  
  - 対象：matcher/soft_skill.py  
  - 承認済みソフトスキル一覧を config 化。全エンジニアにマーク付与  
 TASKS.md  
  1. ソフトスキルチェック関数を stub から実装  
  2. テストケース追加  

8. Notion 400フォールバックで全員マッチング対象  
 CLAUDE.md  
  - …  
 SPEC.md  
  - 対象：notion_client/query_engineers.py  
  - フォールバック時もフィルタ条件（active, tags）を付与する  
 TASKS.md  
  1. HTTP 400 キャッチブロックに filter 条件追加  
  2. テスト  

9. BTM/NBW案件がengineer判定→skip  
 CLAUDE.md  
  - …  
 SPEC.md  
  - 対象：matcher/patterns.py  
  - 正規表現修正：BTM\/NBW 案件はマッチング対象に含める  
 TASKS.md  
  1. 該当正規表現見直し  
  2. 単体テスト  

――――――――――――――――  
Ｑ３．マッチング精度問題のグルーピング  
――――――――――――――――  
1) 「語彙外スキル silent pass」と「soft-skill all-pass」は別タスク推奨  
　– 理由：前者は SkillNormalizer モジュール、後者は soft_skill モジュールに属し依存関係が薄く、レビュー範囲を分割したほうが漏れ防止。  
2) 「並行情報の当日確認」は、まず Notion 並行案件データ取得側に当日フィルタを追加→その上で備考パーサーの解析結果を当日判定に連動させる、の順序  
　– 理由：外部取得段階で不要データを絞り込まないと、パーサー改修だけでは無効データ流入を防げないため。  

――――――――――――――――  
Ｑ４．依存関係・リスク連鎖で見落としパターン  
――――――――――――――――  
・CostGuard v2 統合（#1）をやらずに Batch API 側 log_cost 修正（#4）だけ行うと、新旧経路の二重管理／計上漏れが併存し、効果半減。  
・Notion登録リトライ（#2）前に processed_id 管理だけ改善すると、アップサートロジック自体が動かず無駄。  
・IMAPタイムアウト設定（#19）を importer (#3) より後に直すと、依然クラッシュ原因を排除できずログ調査も進まない。  

――――――――――――――――  
Ｑ５．2名体制・予算・Cursor実装制約下の３段階スケジュール案  
――――――――――――――――  
※各週Cursorタスク上限 2 同時並行  

Week1（P0中でも最緊急：コスト制御／データ欠損防止）  
 - Task A: #1 CostGuard v2 統合（mail_pipeline 修正）  
 - Task B: #2 Notion登録失敗リトライ＆processed_id 管理修正  

Week2（同じく P0：自動化途切れ防止コスト集計）  
 - Task C: #3 importer 例外ハンドリング＋IMAPタイムアウト実装  
 - Task D: #4 classify_email_v2 Batch API log_cost 包装  

Week3（P0マッチング誤通知修正①）  
 - Task E: #5 語彙外必須スキル処理強化  
 - Task F: #6 soft-skill all-pass 実装  

Week4（P0マッチング誤通知修正②）  
 - Task G: #8 Notion 400 フォールバックフィルタ強化  
 - Task H: #9 BTM/NBW 正規表現修正  

――以降 P1→P2 順に回し、月 API 予算／Cursor 実装ペースに合わせて着手。以上です。