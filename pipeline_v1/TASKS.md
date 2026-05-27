# TASKS.md — Phase1営業パイプライン 実装チェックリスト

最終更新: 2026-05-25

## Phase A: 基盤構築

- [x] 1. `fetcher.py` 作成: Notion案件DBクエリ（ステータス=募集中）→ リスト返却
- [x] 2. `fetcher.py` に情報鮮度チェック追加（案件: 4営業日以内, エンジニア: 3週間以内）
- [x] 3. `fetcher.py` にエンジニアDB取得を追加（稼働状況=稼働可能）
- [x] 4. `fetcher.py` 単体テスト: `python fetcher.py` で案件数・エンジニア数をprint

## Phase B: マッチングロジック

- [x] 5. `matcher.py` 作成: 案件とエンジニアのリストを受け取り候補を返す
- [x] 6. 必須スキル全○チェックを実装（1つでも×→除外）
- [x] 7. 粗利計算実装（project_price - engineer_price < 5 → 除外）
- [x] 8. スコアリング実装（必須全○基準点 + 尚可○率 + 粗利品質）
- [x] 9. 案件ごと上位3名を返す処理
- [x] 10. `matcher.py` 単体テスト: サンプルデータでマッチング動作確認

## Phase C: メール文生成

- [x] 11. `composer.py` 作成: テンプレート1の変数を埋めて文面を生成
- [x] 12. 提案単価計算: 粗利7万目標の単価を自動算出してテンプレートに挿入
- [x] 13. 必須/尚可スキルの○×フォームを自動生成
- [x] 14. `composer.py` 単体テスト: 出力をprintで確認

## Phase D: 統合・出力

- [x] 15. `pipeline.py` 作成: Step1〜4を統括するメインスクリプト
- [x] 16. `--dry-run` / `--run` 引数対応
- [x] 17. `result_pipeline.json` への出力実装
- [x] 18. `python pipeline.py --dry-run` でエンドツーエンド動作確認
- [x] 19. result_pipeline.jsonの内容をprint確認

## 完了済み
1〜19完了
