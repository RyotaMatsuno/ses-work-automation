# delete_zero_ref_canonicals.py ゲートNG修正（安全化・2026-07-07）

## ゲート指摘（GPT/Sonnet一致NG 12:39、results/gate_implementation_20260707_123924.json）
1. main()がデフォルトdry_run=False・確認なしで本番skill_aliases.jsonを上書き
2. バックアップ作成→normalizerインポートの順序が逆（ImportError時にバックアップだけ残る）
3. バックアップ名が日付のみ→同日2回実行で1回目が上書き消失
4. soft_aliases削除が承認スコープに含まれることの明記なし

## 修正内容
1. argparse導入。**デフォルトをdry-runに反転**。本番実行は `--execute` フラグ必須。
   ※ input()等のインタラクティブ確認は入れないこと（auto_runner/jobz経由の自動実行がハングするため。
   フラグ明示を確認の代替とする設計）
2. バックアップ名を bak_canonical38_YYYYMMDD_HHMMSS に変更（時刻付与で上書き消失防止）
3. normalizerインポートと参照データ（poc_engineers.json / structured.jsonl）の読み込み成功を
   **バックアップ作成より前に**確認する順序へ変更
4. docstringに「soft_aliases含む全エイリアス削除が松野承認範囲（2026-07-06）」と明記
5. 実行時照合: TARGET_CANONICALS(38件)と canonical_audit_report.md の参照0リストを突合し、
   不一致があればエラー表示して中断（レポート不在時はWARNING+中断。--force-skip-auditで回避可）

## テスト追加（tests/test_delete_zero_ref_canonicals.py）
- 引数なし実行で本番ファイルが変更されないこと（dry-runデフォルト）
- --executeでのみ書き込みが起きること
- バックアップ名の時刻付与
- 監査レポート不一致時の中断

## 完了後
python gate_checker/gate_check.py --phase implementation --file matching_v3/tools/delete_zero_ref_canonicals.py
（コード内容が変わるため装置3の重複スキップは発生しない想定）

## 禁止事項
- TARGET_CANONICALSの38件リスト自体は変更しない
- LLM呼び出し不要
