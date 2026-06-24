> ⚠ **2026-06-16でフリーズ。最新は `cost_guard_v2/` を参照**
>
> このディレクトリは6/5時点の設計で凍結されています。装置1〜3 + DAILY_CALL_LIMIT を含む最新仕様は `ses_work/cost_guard_v2/SPEC.md` v2.2 を参照してください。

---

# SPEC.md — cost_control（コスト統制基盤）

設計: ジョブズ / 2026-06-05

---

## 0. 背景（実測）
- 6/2の1日で **$50.88（¥7,886）** を消費（mail_pipeline $31.65 + matching_v2 $19.22）。
- 直後に **Anthropicアカウント上限に到達** → 6/3以降のAPIは全て `400 usage limits` で失敗中（=現在AI機能停止）。
- 原因: mail_pipeline の `PROCESS_LIMIT=2000` 引き上げ + 配信スパム除外フィルタ不在 →
  active_projects が 6/1:1,637 → 6/5:5,970 に膨張 → matching のトークン爆発。
- LINE松野チャンネルも 200通/月 上限に到達（6/2〜 `429`）。
- 上限は 7/1 にリセット予定 → **根本原因を直さないと7月に同じ暴走を再発**する。

## 1. モデル使用の現状マップ（要修正）
| 箇所 | ファイル:行 | 現モデル | 妥当性 |
|---|---|---|---|
| メール本文分類 | mail_pipeline.py:433/494/538/632 | Haiku 4.5 | OK |
| 添付**テキスト**抽出 | skill_reader.py:95 (extract_skills_from_text) | **Sonnet 4.6** | ★過剰（テキストにSonnet不要） |
| 添付**画像/PDF**抽出 | skill_reader.py:106 (extract_skills_from_image) | Sonnet 4.6 | 要A/B（visionは精度依存） |
| Outlook取り込み分類 | outlook_to_notion.py:112 | **Sonnet 4(0514)** | ★過剰（分類にSonnet不要） |
| マッチング判定 | skill_judge.py:28 | Haiku 4.5 | OK |
| マッチングfallback | skill_judge.py:101-111,174 | **Sonnet（暗黙）** | ★危険（Haiku 404時に全件Sonnet化） |
| v3構造化 | matching_v3/config.py:17 | gpt-4.1-nano | OK（既にコスト統制済み） |

価格（/MTok）: Haiku 4.5 = in $1 / out $5、Sonnet 4.6 = in $3 / out $15（**約3〜4倍**）。

## 2. コンポーネント仕様

### C1. Sonnet合理化（no-regret）
- skill_reader.extract_skills_from_text: Sonnet → **Haiku 4.5**。
- outlook_to_notion 分類: Sonnet → **Haiku 4.5**。
- skill_judge._select_fallback_model: **Sonnetフォールバックを廃止**。
  Haiku系の別バージョンにピン留め or 取得失敗時はハードエラー＋ログ警告（黙ってSonnet化しない）。
- extract_skills_from_image（vision）は当面 Sonnet 維持。ただし `VISION_MODEL` env で
  コード変更なしに切替可能にする（C5のA/B後にフラグで切替）。
- 受け入れ: 全テキスト系がHaiku、visionのみenv切替可、fallbackにsonnet文字列が無いこと。

### C2. モデル名の一元化
- 全モデル名を config（env: TEXT_MODEL / VISION_MODEL / STRUCTURER_MODEL / MATCH_MODEL）へ集約。
- ハードコードを撤去。今後のモデル差し替えは .env 1行で完結させる。
- 受け入れ: grep で claude-/gpt- のハードコードが本番.pyに残っていないこと。

### C3. cost_guard 全展開
- common/ledger.py（既存）の日次/月次合算ガードを、Anthropic/OpenAIを呼ぶ全本番スクリプトに適用:
  mail_pipeline / skill_reader / outlook_to_notion /（復活時の）matching。
- 各API呼び出し前に `ledger_can_spend(est_in, est_out, model)` を確認、超過なら処理停止＋ログ。
- 暫定値: **DAILY $1.00 / MONTHLY $6.00**（配信フィルタ後の実需要は1日数十円想定なので安全網）。
  値は env で変更可能に。
- 上限到達時は岡本LINEチャンネルへ1通だけ警告（松野チャンネルは7/1まで上限のため）。
- 受け入れ: 各スクリプト先頭でガードが効き、上限超で必ず止まること（test_cost_guard相当を流用）。

### C4. 配信スパム除外フィルタ（構造修正の本丸）
- mail_pipeline 取り込み時、分類API**前**に配信メールを判定して除外する。
- 判定（OR）: (a) List-Unsubscribe / List-Id ヘッダ有り、(b) 既知の一斉配信送信元ドメイン
  allowlist の逆（個別案件を送ってくるBPの送信元ホワイトリスト方式が安全）、
  (c) 本文に「配信停止」「メルマガ」等のフッタ、(d) To/CC が多数宛て。
- 配信と判定 → **分類スキップ＆Notion登録スキップ**（ログには残す）。
- `PROCESS_LIMIT` は fetch とは分離し、**分類対象（非配信）を1回あたり最大150件**に制限（安全弁）。
- 受け入れ: 既存受信箱でサンプル100通を流し、配信除外率と誤除外0件を確認。

### C5. 案件自動失効（DB肥大の恒久対策）
- 新規 cost_control/project_expiry.py:
  案件DBで「受信から4営業日超」かつ未成約の案件を「クローズ/アーカイブ」ステータスに更新。
  （判断マニュアルv3の鮮度ルールをDB運用に実装）
- 一括プルーニング（初回）: 現在の stale ≈5,900件を退避ステータスへ。物理削除はしない。
- 日次タスク `SES_ProjectExpiry`（朝）を登録。
- 受け入れ: 実行後 active_projects が実需要規模（数十〜百件台）に収束すること。

### C6. vision A/B（C1のenv切替を確定させる検証）
- 上限リセット後（7/1〜）、実スキルシート画像 約30件で Haiku-vision と Sonnet-vision を比較。
- 比較項目: スキル / 経験年数 / 単価 の抽出正答率。
- Haiku が Sonnet の **90%以上**の正答率なら VISION_MODEL=Haiku に切替。未満なら Sonnet 継続。
- 受け入れ: A/B結果を cost_control/vision_ab_result.md に記録し、env値を確定。

## 3. リリース順序（TASKS.md参照）
Phase 1（no-regret/即）: C1 → C2 → C3
Phase 2（構造）: C4 → C5（＋初回プルーニング）
Phase 3（検証/7月）: C6 → 上限解除後の実コスト計測 → ガード値の本調整

## 4. 完了の定義
- 配信フィルタ後、1日のAPIコストが **$1未満**で安定。
- active_projects が実需要規模に収束。
- Sonnet使用が vision のみ（or A/B後ゼロ）。
- 全API呼び出しに日次/月次ガードが効いている。
