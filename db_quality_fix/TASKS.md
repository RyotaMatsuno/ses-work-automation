# TASKS.md — エンジニアDB クレンジング 実装チェックリスト

バージョン: v1.2
作成日: 2026-06-10

---

## セットアップ
- [ ] `output/` ディレクトリを起動時に自動作成
- [ ] `.env` から `NOTION_API_KEY` と `NOTION_ENGINEER_DB_ID` を読み込む
- [ ] CLI引数 `--live` / `--patterns` / `--max-updates` / `--db-id` を argparse で実装
- [ ] 起動時にNotionDBスキーマを取得し、PROP全キーの存在確認。なければ即終了

## データ取得
- [ ] `POST /v1/databases/{id}/query` で全件取得（page_size=100）
- [ ] `has_more=True` の間 `start_cursor` で継続取得
- [ ] 取得件数をコンソール出力

## notion_requestラッパー実装
- [ ] 429時: `Retry-After` ヘッダーを読んで待機 + リトライ（最大5回）
- [ ] 5xx時: exponential backoff（最大5回）
- [ ] query後: `time.sleep(0.35)`
- [ ] update後: `time.sleep(0.5)`

## バックアップ
- [ ] dry_run・live実行前に対象レコードの全プロパティを `output/backup_*.jsonl` に保存

## チェック実装
- [ ] P1: NATIONALITY_BLOCK に一致 AND フラグTrue → 検出
- [ ] P2: NATIONALITY_UNKNOWN に一致 AND フラグTrue → 検出
- [ ] P3: 経験年数<0 OR >45 → null化対象。年齢フィールドがあれば `経験年数 > 年齢-15` も対象。36〜45はwarning
- [ ] P4: 稼働可能日 < today-180日 → null化。today+365日超 → warning
- [ ] P5: PLACEHOLDER_NAMES 完全一致 OR 名前に「案件」「募集」「株式会社」「要員情報」を含む → 検出
- [ ] P6: HIGH_SIGNAL×2 + MEDIUM_SIGNAL×1 でスコア計算。4以上→False、2〜3→warning
- [ ] P7: 単価null AND フラグTrue → warning。単価<20 OR >150 → warning
- [ ] idempotency: 各パターン、備考・除外理由に `[cleaner:Pn:` が既にあればスキップ
- [ ] `--patterns` 引数で指定パターンのみ実行

## Notion定数化
- [ ] PROP辞書でプロパティ名を一元管理（ハードコード禁止）
- [ ] NATIONALITY_BLOCK / NATIONALITY_UNKNOWN / PLACEHOLDER_NAMES を定数として定義

## dry_run出力
- [ ] P別の検出件数をコンソール出力（dry_run時は `[DRY-RUN]` プレフィックス）
- [ ] `output/report_*.txt` にテキストレポート保存
- [ ] `output/report_*.json` に構造化データ保存
- [ ] 最後に「`python cleaner.py --live` 実行前にoutput/レポートを確認してください」を出力

## live更新（`--live` 時のみ）
- [ ] `--max-updates` の上限チェック。超えたら残件数を出力して停止
- [ ] P1/P2/P5/P6: 提案対象フラグ→False、除外理由に付記
- [ ] P3/P4: 値をnull化、備考末尾に付記（idempotency対応）
- [ ] P7: 変更なし
- [ ] 更新成功/失敗をコンソール出力
- [ ] 更新件数サマリーを出力

## 完了条件
1. `python cleaner.py` がエラーなく完了し output/ にレポートが生成される
2. `python cleaner.py --live --patterns P1,P2 --max-updates 10` で実際にNotionが更新される
3. dry_runモードではNotion書き込みが発生しない
4. 同じスクリプトを2回実行しても備考が増殖しない（idempotency）
5. 429エラー時にリトライして処理が継続される
