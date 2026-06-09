# TASKS.md - gate_checker 実装チェックリスト

## Phase 0: 設計レビュー
- [ ] ゲート①：SPECをGPTで設計レビュー → OK取得

## Phase 1: セットアップ
- [ ] ses_work/gate_checker/ ディレクトリ作成
- [ ] ses_work/gate_checker/results/ ディレクトリ作成
- [ ] ses_work/gate_checker/gate_check.py 作成（entrypoint）

## Phase 2: gate_check.py 実装
- [ ] argparse（--phase / --file / --tasks）実装
- [ ] 対象ファイル読み込み（パス解決: cwd → gate_checker/）
- [ ] requirements フェーズ用プロンプト実装
- [ ] implementation フェーズ用プロンプト実装
- [ ] GPT-4o API呼び出し（OpenAI REST / openai SDK）
- [ ] 判定パース（GO / 条件付きGO / NG）
- [ ] exit 0（OK）/ exit 1（NG）返却

## Phase 3: 付帯機能
- [ ] 日次10回上限（daily_counter.json）
- [ ] CostGuard連携（can_spend / record）
- [ ] results/ に結果JSON保存
- [ ] NG時 TASKS.md フラグを [!] に更新

## Phase 4: テスト
- [ ] python gate_checker/gate_check.py --phase requirements --file SPEC.md 動作確認
- [ ] OK時 exit 0 確認
- [ ] NG時 exit 1 + TASKS.md [!] 更新確認
- [ ] 日次10回上限の動作確認

## Phase 5: 完了確認
- [ ] ゲート②：コードレビュー（別個体）→ OK取得
