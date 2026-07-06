# 修正タスク: alias_filter.py ゲート②NG対応 + 通過221件の残存false match遮断

作成: 2026-07-06 / 対象NG: gate_implementation_20260706_125035.json
前提: judge_with_metaエンジニア側2トークン化は反映済み（matcher.py L1219-1225確認済み）。本タスクはalias_filter.py側のみ。

## Phase A: ゲートNG指摘の修正

A1. R9/R2の適用順序バグ（test_r9_allowlist_cplusplus FAIL中）
- _R9_ALLOWLIST のキーは _apply_rules() 冒頭で短絡許可（R1〜R3をスキップ）
- _symbol_ratio() の非記号扱い文字に `#` `+` を追加
- 完了条件: pytest tests/test_alias_filter.py 全パス

A2. R12の短canonicalスキップ修正（Go/SE/PL素通り問題）
- 比較前に key/canonical 双方を lower + 空白/./-除去 で正規化してから包含判定
- canonical_base が2字以下（SE/PL/PM/QA/Go等）は包含判定禁止・**完全一致のみ**通過
- 落とすべき実例: freshservice→SE / superset→SE / seo対策→SE /
  googlespredseet→SE / powerplatform→PL / pl/1→PL / pl/i→PL / データカタログ→ログ

A3. _symbol_ratio() の日本語判定を明示レンジに置換
- U+3040-309F(ひらがな) / U+30A0-30FF(カタカナ) / U+4E00-9FFF(CJK) / U+30FC(長音) / U+3005(々)
- 文字コード順比較 `"　" <= ch <= "鿿"` は廃止

A4. _SPACE_MAX → _SPACE_REJECT_THRESHOLD にリネーム（意味: この数以上でREJECT。閾値2は維持）

## Phase B: 通過221件精査で発見した残存false match対策（新ルール）

B1. R15: 未閉じ括弧・カンマ含みキー → REJECT
- _NOISE_CHARS_RE に （ ） ( ) , 、を追加（対のとれた括弧も断片扱いでREJECTでよい）
- 実例: aws(dynamodb, sqs / excel(関数 / lambda(python / 生成ai(llm / jp1(base / iac(ansible

B2. R16: canonicalが現行skill_aliases.jsonのcanonical_skills(533件)に存在しない → review行き
- alias_rejected_report.csvではなく review_queue.csv（新規出力）に振替
- 遮断対象実例: Company / Project Details / Long-term Participant / RemoteWork / GS21

B3. R17: コンピテンシー・汎用職務canonical禁止（_DANGER_CANONICALSに追加）
- 追加: コミュニケーション力 / 主体性 / リーダー / 調整 / 実施 / 実行 / メール /
  営業 / ディレクション / 上流工程 / ログ / SE / PL / PM
- 実例遮断: 高いコミュニケーション力→コミュニケーション力 / チームリーダー→リーダー /
  bpr企画 実行→実行 / ビジネスメール→メール

B4. 誤マッピング個別遮断（ハードコード不可。ルールで落ちること）
- devexpress→Express: R12正規化包含でも "express" ⊂ "devexpress" で通ってしまうため、
  **canonical英単語がキーの先頭以外から始まる包含は review行き** とする補則をR12に追加
- powerpages→RPA / postgres sql→SQL: R12（正規化後に包含なし）で自然に落ちることをテストで確認

## Phase C: テスト・再生成・ゲート再実行
1. 上記の全実例を test_alias_filter.py に正例・負例として追加
2. pytest matching_v3/tests/ -q 全パス（既存144件+新規）
3. alias_filter.py 再実行 → tools/output/ 再生成（通過数ログ出力。想定130〜180件）
4. precision_sample_40.md 再生成（層化40件）
5. ゲート②再実行:
   python gate_checker/gate_check.py --phase implementation --file matching_v3/tools/alias_filter.py
6. GO判定が出たら**停止**。precision_sample_40.mdの松野レビュー待ち（Phase 4登録は松野OK後のみ）

## 完了条件
- [ ] test_r9_allowlist_cplusplus 含む全テストパス
- [ ] freshservice→SE / データカタログ→ログ / devexpress→Express が全て非通過
- [ ] output再生成 + 通過数レポート
- [ ] ゲート②GO → 停止して松野レビュー依頼
