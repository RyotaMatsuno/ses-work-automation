# SPEC.md — 壁打ちスクリプト

最終更新: 2026-05-26

## 概要
`python wall_hitting.py --problem "エラー内容や詰まっている問題"` を実行すると、
OpenAI（GPT-4o）とGemini（gemini-2.0-flash）に同じ問題を投げて
それぞれの視点から解決策を取得し、ターミナルに出力するスクリプト。

## 出力フォーマット
```
====== 壁打ち結果 ======

【問題】
{problem}

【GPT-4o視点（実装最短パス）】
{openai_response}

【Gemini視点（アーキテクチャ・長期保守）】
{gemini_response}

【ジョブズ判断メモ欄】
（ここに自分の判断を書く）
========================
```

## プロンプト設計
両モデルへの共通システムプロンプト:
```
あなたはPythonシステム開発の専門家です。
以下の技術的問題について、300文字以内で具体的な解決策を提案してください。
コードスニペットがあれば含めてください。
```

OpenAI用追加指示: 「速度・シンプルさを最優先に、最短の修正パスを示してください」
Gemini用追加指示: 「長期保守性・拡張性を重視し、アーキテクチャ観点から助言してください」

## API仕様
### OpenAI
- エンドポイント: https://api.openai.com/v1/chat/completions
- モデル: gpt-4o（o3はコスト高のため不使用）
- max_tokens: 500

### Gemini
- エンドポイント: https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent
- max_output_tokens: 500
- Gemini 429エラー時: 10秒待ってリトライ1回。それでも失敗なら「Gemini一時利用不可」と表示して続行

## ファイルパス
- スクリプト: `C:\Users\ma_py\OneDrive\デスクトップ\ses_work\wall_hitting.py`
- .env: `C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env`

## 完了条件
1. py_compile wall_hitting.py エラーなし
2. python wall_hitting.py --problem "テスト問題" が正常終了
3. GPT-4oからの応答が出力に含まれること
