# CLAUDE.md — 壁打ちスクリプト

## 役割
技術的行き詰まり時にJobzが自律的にOpenAI/Gemini APIを叩いて
複数視点の意見を取得し、解決策をSPECに反映するスクリプトを作る。

## 禁止事項
- APIキーをログやコードにハードコードしない（dotenv_valuesで読む）
- レスポンスを加工せずそのまま出力しない（要点だけ抽出して出力）
- Gemini/OpenAIのどちらかが失敗しても全体をクラッシュさせない
- 500文字を超えるプロンプトを送らない（コスト節約）

## ファイル構成
- `ses_work/wall_hitting.py`（新規作成）

## コーディングルール
- Python 3.11
- requests使用（anthropicやopenaiライブラリ不使用、HTTP直叩き）
- config/.envからOPENAI_API_KEY/GEMINI_API_KEYを読む
- CLI引数: --problem "問題の説明"
- タイムアウト: 30秒
