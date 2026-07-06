# TASKS.md — matching_v3 実装チェックリスト

**Codex へ: 上から順に実装し、完了したら `[ ]` を `[x]` に更新すること。
1タスクが完了してテストが通るまで次に進まない。**

---

## Phase A: 基盤モジュール（依存なし）

- [x] **A1. config.py** — 設定ロード
  - `dotenv_values("../config/.env")` で全 API キーを読み込む
  - `users.yaml` を読み込む（存在しない場合は `users.yaml` をコピーして自動生成しない、エラーを出す）
  - Notion DB ID を定数として定義:
    - `ENGINEER_DB_ID = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"`
    - `CASE_DB_ID = "343450ff-37c0-81e4-934e-f25f90284a3c"`
  - `STRUCTURER_MODEL` 環境変数があれば優先（デフォルト: `claude-haiku-4-5-20251001`）
  - 単体テスト不要（シンプルなローダー）

- [x] **A2. processed_db.py** — SQLite 処理ステータス DB
  - SPEC.md §7 の SQL スキーマを `__init__` で自動作成
  - DB パス: `matching_v3/matching_v3_processed.db`
  - 実装メソッド: `is_processed`, `mark_api_called`, `update_status`, `add_cost`, `get_today_stats`
  - テスト: `tests/test_processed_db.py`
    - [x] 新規ケースの登録 → `is_processed` が True を返す
    - [x] `update_status` で business_status が更新される
    - [x] `add_cost` が累積される

- [x] **A3. cost_guard.py** — コスト上限管理
  - SPEC.md §8 の 8 重防御を実装
  - `can_call`, `record_cost`, `get_model`, `_get_monthly_cost` を実装
  - `record_cost` は `../usage_tracker/cost_log.jsonl` に `script="matching_v3"` で追記
  - テスト: `tests/test_cost_guard.py`
    - [x] `can_call` が日次 $6 超過で False を返す
    - [x] `can_call` が月次 $140 超過で False を返す
    - [x] `get_model` が月次 $120 超過で fallback モデルを返す

- [x] **A4. notion_client.py** — Notion REST API ラッパー
  - ベース URL: `https://api.notion.com/v1/`
  - Notion-Version: `2022-06-28`
  - タイムアウト 30 秒、指数バックオフリトライ 3 回（1, 2, 4 秒）
  - 実装メソッド:
    - `get_new_cases(days: int) -> list[dict]` — 4 営業日以内の案件取得
    - `get_active_engineers() -> list[dict]` — アクティブエンジニア取得（鮮度フィルタ付き）
    - `update_match_status(case_id: str, results: list) -> None` — Notion にマッチ結果を書く（失敗しても例外を上に投げない）
  - テスト: モックを使った単体テスト（実 API は叩かない）
    - [x] `get_new_cases` のフィルタ構築テスト
    - [x] リトライロジックテスト（mock で 2 回 500 → 3 回目で成功）

---

## Phase B: コアロジック

- [x] **B1. tests/fixtures.json** — テスト用ダミーデータを作成
  - 案件メール例 2 件（通常案件・面談設定済み案件）
  - エンジニアデータ例 3 件（MATCH 想定・NG 想定・REVIEW 想定）
  - 期待する JSON 構造化出力 2 件（Few-shot 例として structurer.py でも使う）

- [x] **B2. structurer.py** — LLM JSON 構造化
  - SPEC.md §4 の仕様で実装
  - システムプロンプトは SPEC.md §4 の文章をそのまま使用
  - `fixtures.json` から Few-shot 2 例をロードしてプロンプトに含める
  - 本文切り詰め（3,000 字: 前 2,000 + 後 1,000）
  - コスト記録（`cost_guard.record_cost` を呼ぶ）
  - **PII 境界: エンジニア情報を一切 LLM に渡さない**
  - テスト: `tests/test_structurer.py`
    - [x] `fixtures.json` のダミー入力 → 期待 JSON が返る（`anthropic` をモック）
    - [x] 3,000 字超の本文が正しく切り詰められる
    - [x] レスポンスの JSON パース失敗時に `extraction_confidence=0.0` で返る

- [x] **B3. matcher.py** — Python マッチングロジック
  - `SkillNormalizer` クラス（SPEC.md §5）
  - `judge()` 関数（SPEC.md §6.3）
  - `_calc_parallel_score()`, `_days_since()` ヘルパー
  - **LLM 呼び出し禁止（if 文のみ）**
  - テスト: `tests/test_matcher.py`
    - [x] NG: 単価超過（エンジニア80万 > 案件上限50万+15万）
    - [x] NG: 必須スキル不足（Java 必須 → エンジニアが Python のみ）
    - [x] MATCH: 全必須スキル○ + 並行スコア < 5.0
    - [x] REVIEW: `ambiguous_skills` あり
    - [x] REVIEW: エンジニアデータが 10 日前更新
    - [x] `SkillNormalizer` のエイリアス変換（"JS" → "JavaScript"）

- [x] **B4. notifier.py** — LINE 通知
  - SPEC.md §9 の 4 ケースロジックと通知フォーマットを実装
  - `enqueue(case, engineer, verdict, reasons)` でキューに積む
  - `flush()` でダイジェスト送信（1 日 8 通上限チェック含む）
  - Push 即時条件: `case_json.get("interview_scheduled_at")` が設定済み（面談設定済み案件）
  - `LINE_CHANNEL_ACCESS_TOKEN` は config.py から読む

---

## Phase C: 統合

- [x] **C1. matching_v3.py** — メインオーケストレーター
  - SPEC.md §10 の `main()` フローを完全実装
  - `--dry-run` フラグ（Phase 0 用）: LINE 通知・Notion 書き込みをスキップ
  - `--input <path>` フラグ（Phase 0 用）: JSONL ファイルから案件を読み込む
  - LockFile による二重起動防止（`matching_v3.lock`）
  - 全モジュールを統合して実行

- [x] **C2. Phase 0 ドライランの動作確認**
  - `python matching_v3.py --dry-run --input tests/fixtures.json` が実行できること
  - `logs/phase0_results.jsonl` が生成されること
  - エラーなしで完了すること

---

## Phase D: スケジューラ・最終確認

- [x] **D1. 全テスト実行**
  - `pytest tests/ -v` を実行
  - 全テストがパスすること
  - 失敗したテストは修正してからチェック

- [x] **D2. Windows タスクスケジューラ登録**
  - タスク名: `SES_MatchingV3`
  - 実行: 毎朝 8:00
  - コマンド: `python ses_work/matching_v3/matching_v3.py`
  - 以下の schtasks コマンドで作成:
  ```
  schtasks /Create /TN "SES_MatchingV3" /TR "python C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\matching_v3.py" /SC DAILY /ST 08:00 /F
  ```

---

## Phase E: GPTコードレビュー修正（2026-06-05）

**背景**: gpt-4.1-nano移行後のGPTコードレビュー結果を受け、P0/P1バグを修正する。
**修正対象**: structurer.py / cost_guard.py / notion_client.py / matcher.py
**テスト**: 既存pytest tests/ が全パスすること（回帰なし確認）

- [x] **E1. [P0] structurer.py: `_call_openai` に `response_format` と `finish_reason` 対応**
  - `response_format={"type": "json_object"}` を `client.chat.completions.create()` に追加
  - `resp.choices[0].finish_reason == "length"` の場合、`logger.warning("OpenAI response truncated by max_tokens")` を出力する
    （_parse_json_or_fallbackに任せるため例外は投げない）
  - OpenAIモデル判定条件を拡張:
    変更前: `model.startswith("gpt-") or model.startswith("o1") or model.startswith("o3")`
    変更後: `model.startswith("gpt-") or model.startswith("o")`
    （o4, o5等の将来モデルにも対応）

- [x] **E2. [P0] cost_guard.py: コスト上限を月$6目標に修正**
  - 変更前後:
    - `DAILY_COST_LIMIT_USD`: 6.00 → 1.00（余裕を持たせた日次上限）
    - `MONTHLY_DEGRADE_USD`: 120.00 → 5.00（月$6目標の手前でdegrade）
    - `MONTHLY_STOP_USD`: 140.00 → 6.00（月次ハード上限）
  - 変数名リネーム（機能影響なし・混乱防止）:
    - `HAIKU_INPUT_RATE` → `LLM_INPUT_RATE_USD`
    - `HAIKU_OUTPUT_RATE` → `LLM_OUTPUT_RATE_USD`
  - コメントを更新: `# gpt-4.1-nano: input $0.10/1M, output $0.40/1M (2026-06時点)`
  - `_estimate_cost()` 内の `cls.HAIKU_INPUT_RATE` / `cls.HAIKU_OUTPUT_RATE` 参照も合わせてリネーム
  - **注意**: テストファイル `tests/test_cost_guard.py` 内のハードコード値も合わせて更新すること

- [x] **E3. [P1] notion_client.py: `_parse_engineer_page` 重複キー削除**
  - `_parse_engineer_page` の戻り値dictから以下の重複行を削除:
    ```python
    "稼働状況": _checkbox(props.get("稼働状況")),  # ← この1行を削除
    ```
  - `_select` による1行目のみを残す
  - 理由: Notionの稼働状況フィールドはselect型（稼働中/待機中等の文字列）のため

- [x] **E4. [P1] matcher.py: `ambiguous_skills` のみの場合REVIEW寄せに変更**
  - `judge()` 末尾の判定ロジックを変更:
    変更前:
    ```python
    if not non_ambig:
        return "MATCH", reasons   # ambiguousのみならMATCH
    ```
    変更後:
    ```python
    if not non_ambig:
        return "REVIEW", reasons   # ambiguousのみでもREVIEW（本番初期は誤提案防止優先）
    ```

- [x] **E5. [P1] matcher.py: エンジニアスキルのnormalize追加**
  - `judge()` 内のエンジニアスキル取得部分を変更:
    変更前:
    ```python
    eng_skills = set(engineer.get("スキル") or [])
    ```
    変更後:
    ```python
    eng_skills_raw = engineer.get("スキル") or []
    eng_skills = set()
    for s in eng_skills_raw:
        n = normalizer.normalize(s)
        eng_skills.add(n if n else s)
    ```
  - これにより「SpringBoot」と「Spring Boot」の表記ゆれによるNG誤判定を防ぐ

- [x] **E6. [P1] matcher.py: 単価情報不足時にREVIEW寄せ**
  - `judge()` の単価チェック部分を変更:
    変更前:
    ```python
    if case_max > 0 and eng_price > 0:
        gross = case_max - eng_price
        if gross < 5.0:
            return "NG", [...]
    ```
    変更後:
    ```python
    if not case_max or not eng_price:
        reasons.append("単価情報不足（確認要）")
    else:
        gross = case_max - eng_price
        if gross < 5.0:
            return "NG", [f"粗利不足: 案件{case_max}万-エンジニア{eng_price}万={gross}万 (最低5万必要)"]
    ```

- [x] **E7. テスト実行・回帰確認**
  - `pytest tests/ -v` を実行
  - 全テストがパスすること
  - E4/E5/E6の変更でtest_matcherが壊れた場合は期待値を新仕様に合わせて修正
  - テスト結果をTASKS.mdの末尾に記録すること

---

## Phase E テスト結果（2026-06-05）

- `pytest tests/ -v`
- 結果: pass（19 passed in 0.21s）
- 備考: E4/E5/E6 の仕様変更に合わせて `tests/test_matcher.py` の期待値を更新し、単価情報不足とエンジニアスキル正規化の回帰テストを追加。

---

## Phase F: 鮮度・粗利フィルタ修正（2026-06-09）

**背景**: 判断マニュアルv3 §2（人材鮮度21日）・§4（粗利5万床）のフィルタを確実に適用する。

- [x] **F1. staleness bug 修正（matcher.py）**
  - `is_engineer_fresh()` を追加（`最終更新日` / `last_updated` / `_last_edited_time` を参照）
  - 最終更新日不明は除外（保守的）
  - `filter_fresh_engineers()` を `is_engineer_fresh()` ベースに修正
  - 除外エンジニアをログ記録（日数経過 or 最終更新日不明）
  - `notion_client.py`: `最終更新日` プロパティのパース追加

- [x] **F2. 粗利フィルター修正（matcher.py）**
  - `calc_gross_profit()` / `meets_profit_floor()` を追加
  - `judge()` でマッチング前に粗利チェック（松野5万 / 岡本3万）
  - 除外時ログ形式: `粗利X万円 < 最低粗利Y万円`

- [x] **F3. テスト追加・実行**
  - 鮮度: 20日OK / 22日NG / 日付不明NG / ログ記録
  - 粗利: 70-60=10万OK / 60-56=4万NG / 60-55=5万OK / 岡本3万床
  - `pytest tests/ -v` 全件パス

---

## 実装完了後に報告すること

- 全テストのパス結果（件数・カバレッジ）
- Phase 0 ドライランが正常動作したこと
- タスクスケジューラ登録の完了
- 未実装・変更が必要な点（あれば明記）
- SPEC.md の記述に曖昧な点があった場合は何を仮定して実装したか明記
## OOV Top 100（2026-07-03 調査）

| # | スキル語 | 出現回数 | 出現元 |
|---|---------|---------|--------|
| 1 | 大規模製造業 | 852 | 案件 |
| 2 | 自動車業界 | 852 | 案件 |
| 3 | PG | 686 | 案件 |
| 4 | 情報処理安全確保支援士 | 673 | 案件 |
| 5 | SC周りのFDS/CS品質チェック | 670 | 案件 |
| 6 | 英語読み書き経験 | 670 | 案件 |
| 7 | 企業におけるBCP策定経験 | 670 | 案件 |
| 8 | IAM | 658 | 案件 |
| 9 | Amazon Redshift | 657 | 案件 |
| 10 | バッチ作成 | 646 | 案件 |
| 11 | 技術検討 | 632 | 案件 |
| 12 | WBS統制 | 632 | 案件 |
| 13 | 進捗管理·課題管理·ベンダーコントロール | 632 | 案件 |
| 14 | 手順書未整備環境での実務経験 | 610 | 案件 |
| 15 | 新横浜 | 521 | 案件 |
| 16 | クライアントワークの経験 | 494 | 案件 |
| 17 | webシステム開発の上流~下流工程のご経験をお持ちの方 | 457 | 案件 |
| 18 | ベンダーコントロール経験 | 423 | 案件 |
| 19 | 課題管理経験 | 419 | 案件 |
| 20 | EC領域 | 418 | 案件 |
| 21 | 拠点常駐での現地対応経験 | 418 | 案件 |
| 22 | スケジュール管理経験 | 418 | 案件 |
| 23 | 主体的に課題解決を行いながら開発を推進できる | 326 | 案件 |
| 24 | システム運用保守 | 248 | 案件 |
| 25 | 運用ツールの作成・開発実務経験 | 246 | 案件 |
| 26 | システム開発PJにおいて | 205 | 案件 |
| 27 | ラキール出身 | 200 | 案件 |
| 28 | ラキール製品知見 | 200 | 案件 |
| 29 | Kernel/OSSの知識 | 182 | 案件 |
| 30 | Debianの知識 | 182 | 案件 |
| 31 | モデル実装・評価 | 162 | 案件 |
| 32 | と考えられる。 | 157 | 案件 |
| 33 | なスキルについて------------------------------------------------- | 157 | 案件 |
| 34 | なインプット情報の精査 | 138 | 案件 |
| 35 | リーダー経験能動的に動け | 138 | 案件 |
| 36 | 管理 | 138 | 案件 |
| 37 | 東京海上IBMホスト | 130 | 案件 |
| 38 | 影響調査・分析経験 | 126 | 案件 |
| 39 | 技術調査結果のドキュメント作成経験 | 126 | 案件 |
| 40 | 一般工具 | 126 | 案件 |
| 41 | 社内ユーザー対応 | 126 | 案件 |
| 42 | 主体的にキャッチアップできる方 | 126 | 案件 |
| 43 | トラブルシュート経験 | 125 | 案件 |
| 44 | システム管理業務経験 | 110 | 案件 |
| 45 | 運用管理経験 | 110 | 案件 |
| 46 | に対する経験有無 | 103 | 案件 |
| 47 | 稼働実績の有無 | 103 | 案件 |
| 48 | Infor M3 | 96 | 案件 |
| 49 | コードレビュー経験 | 86 | 案件 |
| 50 | 試験 | 76 | 案件 |
| 51 | 自発的に動ける方 | 73 | 案件 |
| 52 | 期間   :2026年7月~ | 72 | 案件 |
| 53 | 明るい方募集 | 72 | 案件 |
| 54 | 開発が一人称問題ない方 | 72 | 案件 |
| 55 | 。英語が必須スキル。7月または8月からの開始。 | 71 | 案件 |
| 56 | appsflyer | 71 | 案件 |
| 57 | criteo)の知識も求められる。 | 71 | 案件 |
| 58 | 。解析ツール(adjust | 71 | 案件 |
| 59 | purviewの実装経験が必要 | 71 | 案件 |
| 60 | 運用案件。entra id | 71 | 案件 |
| 61 | 上位直案件 | 71 | 案件 |
| 62 | 。常駐案件。 | 71 | 案件 |
| 63 | 長期延長可能性あり | 71 | 案件 |
| 64 | SNS | 69 | 案件 |
| 65 | な人は面談2回の想定 | 67 | 案件 |
| 66 | マーケティング | 67 | 案件 |
| 67 | itサービス | 65 | 案件 |
| 68 | ハードウェア知識 | 59 | 案件 |
| 69 | M365管理運用 | 58 | 案件 |
| 70 | 商品企画 | 58 | 案件 |
| 71 | UX | 58 | 案件 |
| 72 | Web広告における運用またはプランニング経験 | 58 | 案件 |
| 73 | 顧客課題を深掘りし本質的な対話ができるコンサルティング力 | 58 | 案件 |
| 74 | PdM | 58 | 案件 |
| 75 | ゲーム | 58 | 案件 |
| 76 | IoT | 58 | 案件 |
| 77 | マーケティングコンサル | 58 | 案件 |
| 78 | データドリブンマーケター | 58 | 案件 |
| 79 | ECサイト運営 | 56 | 案件 |
| 80 | ITコンサルティング | 56 | 案件 |
| 81 | IT分離 | 56 | 案件 |
| 82 | 交渉力 | 56 | 案件 |
| 83 | NWの基本知識 | 54 | 案件 |
| 84 | ハードウェア修理 | 52 | 案件 |
| 85 | メンテナンス | 52 | 案件 |
| 86 | ACOS-4 | 52 | 案件 |
| 87 | acos-4の起動 | 52 | 案件 |
| 88 | コマンド操作 | 52 | 案件 |
| 89 | 起動・停止操作 | 52 | 案件 |
| 90 | 当事者意識 | 47 | 案件 |
| 91 | 8月~ | 32 | 案件 |
| 92 | 勝どき | 32 | 案件 |
| 93 | 運行管理システム開発 | 32 | 案件 |
| 94 | Web アプリケーション開発 | 24 | 案件 |
| 95 | 公共データ連携基盤開発 | 24 | 案件 |
| 96 | 即日 | 18 | 案件 |
| 97 | hr業界 | 17 | 案件 |
| 98 | 70~75万 | 16 | 案件 |
| 99 | 東日本橋 | 16 | 案件 |
| 100 | データ分析 | 11 | 案件 |
