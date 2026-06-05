# TASKS.md — cost_control 実装チェックリスト

設計: ジョブズ / 2026-06-05 / 実装: Codex

## Phase 1 — no-regret（即・計測不要）
- [x] C2: config集約モジュール作成（TEXT/VISION/STRUCTURER/MATCH_MODEL を env化）
- [x] C1-1: skill_reader.extract_skills_from_text を Sonnet→Haiku（TEXT_MODEL参照）
- [x] C1-2: outlook_to_notion 分類を Sonnet→Haiku（TEXT_MODEL参照）
- [x] C1-3: skill_judge._select_fallback_model のSonnetフォールバック廃止（Haikuピン or ハードエラー）
- [x] C1-4: extract_skills_from_image を VISION_MODEL 参照に（既定はSonnet維持）
- [x] C3-1: common/ledger.py ガードを mail_pipeline / skill_reader / outlook_to_notion に適用
- [ ] C3-2: 上限到達時の岡本LINE警告（1通）実装
- [ ] 検証: grep でハードコードモデル残存ゼロ / py_compile 全通過

## Phase 2 — 構造修正
- [ ] C4-1: 配信判定関数 is_broadcast(msg) 実装（ヘッダ＋送信元allowlist＋フッタ）
- [ ] C4-2: 分類API前に is_broadcast で除外、Notion登録もスキップ
- [ ] C4-3: PROCESS_LIMIT を fetch と分離、非配信の分類を1回150件上限に
- [ ] C4-4: 受信箱サンプル100通で配信除外率・誤除外0件を確認
- [ ] C5-1: cost_control/project_expiry.py 実装（4営業日超→アーカイブ）
- [ ] C5-2: 初回一括プルーニング（stale約5,900件を退避ステータス、物理削除なし）
- [ ] C5-3: SES_ProjectExpiry 日次タスク登録
- [ ] 検証: active_projects が実需要規模に収束

## Phase 3 — 検証（7/1 上限リセット後）
- [ ] C6-1: 実スキルシート画像30件で Haiku-vision vs Sonnet-vision A/B
- [ ] C6-2: 結果を vision_ab_result.md に記録、VISION_MODEL を確定
- [ ] 上限解除後72時間の実APIコストを計測（目標 $1未満/日）
- [ ] ledger の DAILY/MONTHLY 値を実測に合わせ本調整
- [ ] SESナレッジWikiに事故記録と恒久対策を追記
