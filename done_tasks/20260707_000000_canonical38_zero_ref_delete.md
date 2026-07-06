# canonical参照0の38件削除（承認済み・影響ゼロ実証済み）

根拠: matching_v3/tools/output/canonical_audit_report.md（2026-07-06 dry-run）
承認: 松野承認済み（参照0=人材参照0かつ案件参照0の38件のみ。参照あり47件は対象外・別途設計）

## 対象（38件・canonical_audit_report.md の参照0リストと完全一致させること）

Ad-hoc / BusinessUser / Company / Construction Industry Experience /
Construction Site Experience / Consumer Content Creator /
Customer Negotiation Experience / GS21 / Hourly Settlement /
InterviewAvailability / Life Insurance Operations / OnSiteWork /
Operations Experience / POSITIVE / ParallelStatus / ProactiveBehavior /
Satellite Office / Self-management / Senior Practitioner / Shift Example /
Telecommunications Experience / AIサービス業務 / DBA / PL経験 / SRE /
ec系業務 / インフラエンジニア / スタートアップ業務 / フィールドプランナー /
ログ / 人材採用 / 営業部門業務 / 採用人事 / 採用人事業務 / 業務推進 /
生成AI業務 / 金融商品取引経験 / 金融業界業務

## 実装（matching_v3/tools/delete_zero_ref_canonicals.py 新規作成）

1. バックアップ必須: skill_aliases.json → skill_aliases.json.bak_canonical38_YYYYMMDD（処理前に作成、失敗時は即中断）
2. **実行時の参照再検証**: canonical_audit.py の参照カウントロジックを流用し、
   実行時点で人材参照0かつ案件参照0であることを38件それぞれ再確認する。
   参照が付いた項目は削除せずスキップし、WARNINGログに残す
   （理由: 明朝8:00バッチで824件辞書が初稼働するため、監査時点との参照ズレがあり得る）
3. 削除内容: canonical_skillsエントリ本体 + そのcanonicalを指す全エイリアス（例: ログ はエイリアス2件）
4. 検証:
   - json.load成功（JSON妥当性）
   - canonical件数 533 → 495（スキップがあればその分差し引き、ログに明記）
   - 削除対象を指すエイリアスが0件残存であること
5. 削除ログ: matching_v3/tools/output/canonical38_delete_log_YYYYMMDD.json
   （deleted / skipped_with_reason / counts_before_after を記録）

## テスト（tests/test_delete_zero_ref_canonicals.py）

- 参照0のcanonicalが削除されること
- 参照>0のcanonicalがスキップされること
- 削除後JSONにdangling alias（存在しないcanonicalを指すalias）が無いこと

## 完了後

python gate_checker/gate_check.py --phase implementation --file matching_v3/tools/delete_zero_ref_canonicals.py
※ 2026-07-06はゲート日次上限30/30到達済み。本タスクは7/7以降に実行すること（上限リセット後）

## 禁止事項

- 参照あり47件（主体性・SE・PM等）には一切触れない（コンピテンシーレイヤ移行設計後に別タスク）
- domain_jp 58件（インフラ/ネットワーク等）は残す対象。触れない
- LLM呼び出し不要（ルールベースのみ。CostGuard対象処理なし）
