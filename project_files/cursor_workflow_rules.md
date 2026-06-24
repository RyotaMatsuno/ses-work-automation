# Cursor作業指示 運用ルール

最終更新: 2026-06-12

## pending_tasks 自動saveルール（2026-06-11確定）

### 概要
ジョブズが【Cursor作業指示】を生成したとき、jobz-commandが稼働中であれば
自動で task_runner.py save を jobz-command経由で実行し pending_tasks/ に保存する。

### フロー
1. ジョブズが【Cursor作業指示】を生成
2. jobz-commandヘルスチェック（echo test）
3. 応答あり → task_runner.py 経由で pending_tasks/ に自動保存
   - 松野はCursorを開くだけでよい（コピペ不要）
4. 応答なし（オフライン）→ チャット本文にコードブロックで出力
   - 「jobz-commandオフラインのため手動でCursorに貼ってください」と明示

### ファイルパス
- task_runner: ses_work/local_server/task_runner.py
- 保存先: ses_work/pending_tasks/
- ファイル名形式: YYYYMMDD_HHMMSS_<タスク概要>.md

### jobz-command 呼び出し仕様
- URL: http://127.0.0.1:8765/run
- 認証: X-Auth-Token: jobz-terra-2026
- コマンド: python ses_work/local_server/task_runner.py save "<ファイル名>" "<内容>"

## モデル宣言ルール（2026-06-10確定）

### 宣言フォーマット
チャット冒頭1行目に以下のいずれかを置く:

| 宣言文 | モデル | 使用場面 |
|---|---|---|
| 「このタスクはSonnet 4.6で十分です」 | Claude Sonnet 4.6 | 通常タスク全般（デフォルト） |
| 「このタスクはOpus 4.8推奨です」 | Claude Opus 4.8 | 法人化・契約・複雑アーキ設計（月5〜10回） |

### Opus推奨の発動基準
- 法人化計画・新規契約先の判断
- 大規模アーキテクチャ変更
- 税務・法的判断

## gate_checker フェーズ一覧（2026-06-11確定）

| フェーズ | 内容 |
|---|---|
| research | 調査・情報収集結果のレビュー |
| requirements | 要件定義レビュー |
| design | 設計レビュー |
| pre_impl | 実装前最終確認 |
| implementation | コードレビュー |
| test | テスト結果レビュー |

### NGの分岐
- 技術的NG → wall_hitting自走（GPT-o3視点/Gemini視点/ジョブズ判断の3視点）
- 仕様NG（コスト発生・根本設計変更・岡本連絡要）→ 松野確認に上げる

## needs_human_review() 3層チェック（2026-06-11確定）

1. 完全一致キーワード（例: 「費用が発生」「岡本に連絡」「契約変更」）
2. 類義語辞書（例: 「コスト」→費用発生扱い）
3. GPT自己判定（上記2層で判定できない場合のフォールバック）

## ジョブズ直接実装禁止ルール（2026-06-12確定）

### 背景
2026-06-12、ジョブズが「緊急対応」として flag_auto_updater と matching_v3 の
logging修正を jobz-command 経由で直接実施し、かつゲート②も省略した。
動作確認後に事後ゲートを通したが、手順違反であった。

### ルール（絶対遵守）

| 状況 | 正しい対応 |
|---|---|
| バグ発見・修正が必要 | Cursor作業指示書を生成 → pending_tasks/ に保存 → Cursorが実装 |
| 「1行だけ直せば済む」 | それでもCursor指示書を出す。例外なし |
| 「緊急で今すぐ直さないと」 | Cursor指示書を出してCursorを開くよう松野に依頼する |
| ジョブズがjobz-commandで本番ファイルを直接書き換える | **禁止** |

### ゲート②省略禁止

- 実装完了後は必ずGPT-4oゲート②を通す
- 「動作確認済みだから大丈夫」はゲート②省略の理由にならない
- ジョブズが直接実装した場合も例外なくゲート②を通す（今回の教訓）

### チェックリスト（Cursor作業完了時）
- [ ] ゲート② (GPT-4o) でコードレビューを実施したか
- [ ] GO判定を確認したか
- [ ] pending_tasks/ から done_tasks/ にファイルを移動したか
