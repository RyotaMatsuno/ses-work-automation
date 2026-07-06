# CLAUDE.md - gate_checker

バージョン: 2.1（Week1拡張版、GPT-5.4 レビュー反映）
更新日: 2026-06-16

## 事業文脈
SES人材紹介事業の開発ゲート制度を自動化する。6フェーズ（調査・要件定義・設計・実装前確認・実装・テスト）をフェーズ別の最適モデルでレビューし、GO/NGを機械的に判定する。

## v2.1で追加された範囲（Week1スコープ）

| 機能 | 概要 |
|---|---|
| フェーズ別モデルルーティング | gpt-5.4-nano / mini / gpt-5.4 / gpt-5.3-codex をフェーズ別に使い分け |
| モデル不在時 fallback | list_models未マッチなら gpt-4o にfallback（運用継続優先） |
| DAILY_CALL_LIMIT 段階値 | 10 → 30（.envで段階化、Week2以降に60→90） |
| 装置2: 単発コスト警告 | 軽$0.025/中$0.10/重$0.15 超過時にLINE警告 |
| 装置3: CostGuard停止時起票 | Notion AI作業キュー自動起票 + LINE通知 |
| 装置3 重複起票防止 | (date, block_type, phase) 複合キーで同日集約 |
| 通知優先順位 | LINE月200通枠の残通数別閾値で制御 |
| exit code 分離 | exit 2 = CostGuard停止 / 日次上限超過 |

## 6フェーズ × モデル

| フェーズ | --phase | モデル | クラス | 想定単発閾値 |
|---|---|---|---|---:|
| 調査 | research | gpt-5.4-nano | 軽 | $0.025 |
| 要件定義 | requirements | gpt-5.4-mini | 軽 | $0.025 |
| 設計 | design | gpt-5.4 | 中 | $0.10 |
| 実装前確認 | pre_impl | gpt-5.4 | 中 | $0.10 |
| 実装 | implementation | gpt-5.3-codex | 重 | $0.15 |
| テスト | test | gpt-5.4-mini | 軽 | $0.025 |

## 作業ルール

- 実装言語: Python 3.x
- 文字コード: UTF-8（ファイル書き込み時は必ず encoding='utf-8'）
- 日本語パス（デスクトップ等）はcwd/コマンドに直接渡さない（subst X: または絶対パスでUnicode escape）
- .envは `ses_work/config/.env` から読む（python-dotenvまたは手動parse）
- 全LLM呼び出しは CostGuard（common/ledger.py）を通す
- API呼び出し前に `can_spend()` 必須、後に `record()` 必須
- レビュー用モデル: フェーズ別（`phase_models.resolve_model(phase, available_models)` で解決）
- 起動時に `OpenAI.models.list()` で AVAILABLE_MODELS を生成
- 不明モデル名は **fallback gpt-4o**（v2.1で統一、エラー終了はしない）
- エラーは握りつぶさず必ずログに出す
- `sys.stdout.reconfigure(encoding='utf-8', errors='replace')` をスクリプト冒頭に必ず入れる
- agreement_checker は GPT-4o + Claude Sonnet 4.6 の合意判定ライブラリ（実装変更時は gate_checker/SPEC.md を参照）

## 判断ルール（松野確認）

- `needs_human_review(phase, gpt_response)` で判定（v1.0から不変）
- requirements / design / test フェーズは常に松野確認推奨
- GPTレスポンスに「運用フロー」「仕様変更」「データ削除」「本番DB」「契約」「岡本」「コスト増」等が含まれる場合も松野確認

## 処理フロー（v2.1更新）

| 状況 | 挙動 | exit |
|---|---|---:|
| OK（問わず） | 結果JSON保存のみ、LINE通知なし（SPEC §13-1 v2.3同期済み） | 0 |
| NG + 技術的 | wall_hitting.py 自動実行 → results/保存 + LINE 1行通知 | 1 |
| NG + 仕様的 | LINE 1行通知のみ（返信不要） | 1 |
| 装置2発動 | cost_alerts.jsonl追記 + LINE（同日同phase同class初回のみ） | 通常通り |
| CostGuard拒否 | 装置3起票 + LINE通知 | **2** |
| DAILY_CALL_LIMIT超過 | 装置3起票 + LINE通知 | **2** |
| モデル不在 | fallback gpt-4o + WARN + LINE通知 | 通常実行 |
| API障害 | ERROR保存 | 1 |

## 装置3 起票仕様

- Notion DB: AI作業キュー `37a450ff-37c0-819a-981b-c2e06ed282bb`
- task_id: `gate_costguard_{block_type}_{phase}_{yyyymmdd}` （v2.1: 複合キー）
- 優先度: High / 担当: jobz / 状態: queued / 人間確認: required
- 推定原因を自動判定（単発過大 / 回数上限 / 月次上限 / 不明）
- 同日・同block_type・同phase の起票は **2回目以降は集約のみ**（`results/costguard_blocks_dedup.json` で管理）

## 通知優先順位（v2.1 新規）

LINE月200通枠を守るため、抑制順位:

| 優先度 | 通知種別 | 抑制 | 残通数閾値 |
|---:|---|---|---:|
| 1 | 装置3（CostGuard停止） | 重複起票防止のみ | 残10通でも送る |
| 2 | NG+致命的（松野確認要） | 同target+phase で1日1回 | 残20通切ったらスキップ |
| 3 | 松野確認(OK時) | 同target+phase で1日1回 | 残50通切ったらスキップ |
| 4 | モデル不在fallback | 1日1回（モデル名キー） | 残80通切ったらスキップ |
| 5 | 装置2（単発コスト警告） | 同日同phase同class で1日1回 | 残150通切ったらスキップ |

## 禁止事項

- CostGuardなしでLLMを呼び出さない
- DAILY_CALL_LIMIT を .env なしでハードコード変更しない（運用ルール）
- 装置2 / 装置3 のLINE通知で月200通枠を圧迫しない（push_or_log必須）
- agreement_checker（GPT-4o + Claude Sonnet）のプロトコル変更は SPEC.md のゲート②通過後のみ許可
- レビュー対象以外のファイルを書き換えない（TASKS.mdのゲートフラグ更新のみ許可）
- APIキーをログやresults JSONに出力しない
- 仕様NG時にwall_hittingを呼ばない
- MODEL_PRICING の単価表を勝手に変更しない（変更時は必ずOpenAI公式と照合）
- DAILY_CALL_LIMIT超過判定をAPI後にしない（必ずAPI前判定）

## ファイル配置

```
ses_work/gate_checker/
├── gate_check.py            # entrypoint（改修）
├── phase_models.py          # 新規（フェーズ→モデル解決、fallback対応）
├── cost_calc.py             # 新規（モデル別単価表 + コスト計算、未知モデルfallback）
├── costguard_handler.py     # 新規（装置3起票・通知、重複集約）
├── agreement_checker.py     # 既存（触らない）
├── prompts/{phase}.txt      # 既存（必要に応じ追加）
├── results/
│   ├── gate_{phase}_{ts}.json
│   ├── daily_counter.json
│   ├── cost_alerts.jsonl              # 新規（装置2ログ）
│   ├── costguard_blocks.jsonl         # 新規（装置3ログ）
│   ├── costguard_blocks_dedup.json    # 新規（装置3 当日抑制キー）
│   └── wall_hitting_{phase}_{ts}.txt
├── SPEC.md                  # v2.1
├── TASKS.md                 # v2.1
└── CLAUDE.md                # v2.1（このファイル）
```

## テストファイル配置

```
ses_work/gate_checker/tests/
├── test_phase_models.py
├── test_cost_calc.py
└── test_costguard_handler.py
```

## 実装順序の推奨

1. phase_models.py（最も独立、テスト書きやすい、fallback対応）
2. cost_calc.py（同上、fallback rate含む）
3. costguard_handler.py（notion_register/push_or_log依存、重複集約含む）
4. gate_check.py 改修（上記3つを使う、AVAILABLE_MODELS生成・API前判定）
5. .env 更新
6. テスト（単体→結合→回帰）
7. exit code 2 互換性確認（Phase 7）
8. MODEL_PRICING 検証（Phase 9）
9. 文書更新
10. ゲート②（コードレビュー）

## 既知の落とし穴

- jobz-command経由でPython実行する際は日本語パスを避ける（subst X: を使うか絶対パスでUnicode escape）
- Notion API は `Notion-Version: 2022-06-28` ヘッダー必須
- LINE push の月200通上限は push_or_log で残通数確認してから送る
- gpt-5.4-nano / gpt-5.3-codex はモデル名が正式名と異なる可能性あり、起動時検証必須（不在ならfallback gpt-4o）
- v1.0 で exit 1 だったケースが v2.1 で exit 2 になる箇所あり（CostGuard停止 / 日次上限超過）→ 既存呼び出し元への影響確認必須
- gate_check.py 自体に既知のハルシネーション問題あり（2026-06-16 確認）。Week1中はSPEC/コードレビューは別経路（spec_v2_review_by_gpt54.py）で実施

## 互換性メモ（v2.1）

- 関数名 `call_gpt4o()` は v1.0 互換のため残す（実態はフェーズ別モデル）
- Week2 で `call_openai_review()` 等に改名予定
- exit code:
  - 0 = OK（v1.0と同じ）
  - 1 = NG / エラー（v1.0と同じ）
  - 2 = CostGuard停止 / 日次上限超過（v2.1で新規分離）← 既存呼び出し元の対応要否確認
