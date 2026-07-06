# タスク: skill_aliases絞り込み再登録 + suffix除去2トークン化（案C）

作成: 2026-07-05 / 壁打ち: research_results/GPT_WALLHIT_alias_narrowing_20260705.md（GPT-5.4合意済み）

## 背景
- 7/3のOOV拡張923件が品質崩壊（文断片47%・汎用canonical行き9%・記号断片5%）
- skill_aliases.jsonは715件（6/30 HEAD）に復元済み。拡張版は matching_v3/skill_aliases_expanded_20260703.json に退避済み
- 本タスクで923件から高品質分のみ再選別して登録する

## Phase 1: フィルタスクリプト新規作成 matching_v3/tools/alias_filter.py
入力: skill_aliases_expanded_20260703.json と現行 skill_aliases.json の差分923件
以下を上から順に適用。REJECTは理由コード付きで記録。

- R1: 助詞（の/を/が/に/て/へ/と/や/も/は）を含むキー → REJECT
- R2: 日本語12字超 or 英数25字超 or 空白2個以上 or 記号率30%超 → REJECT
- R3: 求人ノイズ記号（万/円/【/】/〜/～/、/。）含み → REJECT。
      数字入り技術名は許可リストで救済: Vue3/Java17/React18/RHEL8/.NET 8/HTML5/CSS3 等
- R4+R10: 高危険canonicalへの新規alias全面禁止:
      AI/AWS/Java/設計/開発/経験/テスト/構築/運用/開発経験/運用経験/運用保守/進捗管理
- R5: 親スキルへの子サービスalias禁止。「aws xxx」「azure xxx」等は
      matching_v3/new_canonical_candidates.csv へ振替（canonical追加候補キュー）
- R6: 業界・職種・資格語 → REJECT（denylist.json参照。SRE/PMO/DBA/QAも今回は除外）
- R9: 4文字以下の英字のみキー → 原則REJECT。例外許可リスト: php/css/sql/c#/c++/vba/etl
      ※ go/aim/it/pm 等は許可しない
- R13: 求人文脈語（案件/募集/対応/担当/可能/歓迎/必須/即日）含み → REJECT
      ※「XX経験/経験者」はREJECTせずPhase 3のlookup-time stripで処理（alias登録しない）
- R12: 残った候補について、canonicalがキーの部分文字列でない場合 → review行き（自動登録しない）

出力3ファイル（matching_v3/tools/output/）:
- alias_candidates_filtered.json（通過分）
- alias_rejected_report.csv（キー/canonical/REJECT理由コード）
- new_canonical_candidates.csv（R5振替分）

テスト: matching_v3/tests/test_alias_filter.py
（各ルールの正例・負例。aim→AI がREJECTされること、Vue3が通ることを必須ケースに）

## Phase 2: 層化precisionサンプル生成（ここで停止・松野レビュー待ち）
- 通過分から層化40件抽出: 短英字系/和文系/クラウド系/略語系 各10件
- matching_v3/tools/output/precision_sample_40.md に「キー → canonical → 判定欄」形式で出力
- **false match 4/40超なら基準強化して Phase 1 再実行。松野OKが出るまで Phase 4 に進まない**

## Phase 3: suffix除去の2トークン化（案C）
- skill_pre_normalize.py:
  - 新関数 pre_normalize_skill_tokens(raw) -> list[str] を追加
  - _TECH_OPS_SUFFIX_RE マッチ時は [ベース技術名, "運用保守"] の2トークンを返す
  - 末尾サフィックスstrip（経験/経験者/の経験/のご経験）を追加。ただしstrip後が
    辞書（canonical or alias）にヒットする場合のみ有効（lookup-time限定。alias登録はしない）
  - 既存 pre_normalize_skill_text は後方互換維持（str返却のまま）
- skill_gate.py / matcher.py: tokens版に切替え、両トークンを要件として保持
- tests/test_skill_pre_normalize.py に2トークンケース追加。既存テスト全パス必須

## Phase 4: 登録 + 再計測（松野レビューOK後のみ）
- skill_aliases.json をバックアップ → 通過分を登録 → 件数ログ出力
- OOV再計測 → matching_v3/oov_report_v2.csv / oov_before_after_v2.md
- 期待着地: alias 715 + 150〜250件。OOV率は28.2%より悪化してよい（false match抑制優先）

## Gate
- 実装前: python gate_checker/gate_check.py --phase design --file pending_tasks/本ファイル（実行済み）
- 実装後: python gate_checker/gate_check.py --phase implementation --file matching_v3/tools/alias_filter.py

## 完了条件
- [x] alias_filter.py + test_alias_filter.py 全パス（46件）
- [x] precision_sample_40.md 生成 → **停止して松野レビュー依頼**
- [x] 2トークン化実装 + 既存テスト全パス（382件）
- [ ] Phase 4 は松野OK後のみ実行
