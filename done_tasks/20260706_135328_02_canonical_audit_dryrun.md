# 02 canonical_skills ゴミ混入 dry-run調査（レポートのみ・削除禁止）

## 背景
skill_aliases.json の canonical_skills 533件に非スキル語が混入
（実例: Company / Project Details / Long-term Participant / RemoteWork / GS21）。
R16（canonical存在チェック）がこれらを素通しした根本原因。

## 作業（新規: matching_v3/tools/canonical_audit.py）
1. canonical_skills 533件を以下に分類（**dry-run・ファイル変更禁止**）:
   - tech: 明確な技術名（Java/AWS等）
   - domain_jp: 和文技術領域（インフラ/ネットワーク等）→ 残す
   - suspect: 非スキル疑い（英語一般語・文断片・意味不明）
   - role_cert: 職種・資格語（確定ポリシーで禁止対象）
2. 判定は ルールベース（英語一般語辞書・大文字始まり複合語・denylist照合）のみ。LLM使用禁止
3. suspect/role_cert について、現在のエンジニアDB・案件マッチングでの参照回数を
   ローカルキャッシュ（poc_engineers.json / structured.jsonl）から集計し併記
4. 出力: matching_v3/tools/output/canonical_audit_report.md
   （分類別件数 + suspect全件リスト + 参照回数 + 削除影響の見立て）

## 禁止事項
- skill_aliases.json の変更（レポートのみ）
- Notion DBへのアクセス（ローカルキャッシュのみ使用）

## 完了条件
- [ ] canonical_audit_report.md 生成
- [ ] 削除は一切していない（git diff クリーン）
