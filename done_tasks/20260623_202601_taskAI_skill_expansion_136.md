# 【Cursor作業指示】Task AI: スキル辞書拡張（Tier1+2投入）+ process_skill別軸保存

対象ディレクトリ: ses_work/matching_v3/
作業内容: skill_aliases.jsonに安全な技術語を段階追加 + process_skillを別軸保存
参照ファイル: CLAUDE.md / skill_aliases.json / matcher.py / research_results/SKILL_TAXONOMY_829_20260623.json / research_results/GPT_TASK_AI_REVIEW_20260623.json
完了条件: 全テスト合格 + 偽陽性ゼロ確認

---

## GPT-5.4レビュー結果（REVISE判定）の対応

### リスクと対策
| リスク | 対策 |
|---|---|
| 抽象語の偽陽性 | Tier3（クラウド,ネットワーク,RDBMS等）は今回追加しない |
| 短縮alias誤爆 | 3文字以下のaliasは完全一致のみ（部分一致禁止） |
| 親子重複 | React/React Native等は親子関係を明示、二重カウント防止 |
| process_skill情報消失 | 除外ではなく別軸保存（process_experienceフィールド） |

## 変更1: Tier1+2のみ追加（約80語）

### Tier1: 明確な技術語（追加する）
Excel, Git, C++, C, PowerShell, Ruby on Rails, Next.js, Laravel, 
Nuxt.js, Vue3, Svelte, Thymeleaf, GitHub, GitLab, JIRA, Backlog,
Ansible, Puppet, Chef, Vagrant, Nginx, Apache, Tomcat,
Redis, Memcached, Elasticsearch, Grafana, Prometheus,
Flutter, Dart, Kotlin Multiplatform, Unity, Unreal Engine,
VBA, Access, Power BI, Tableau, Looker, Redash,
Figma, Adobe XD, Sketch

### Tier2: 製品・サービス群（追加する）
VMware, VMware vSphere, JP1, Zabbix, Nagios, Hinemos,
Snowflake, Databricks, BigQuery, Redshift, 
Power Platform, Power Automate, Power Apps,
OCI, Alibaba Cloud,
Prisma Access, Zscaler, FortiManager,
Palo Alto, F5, A10, Juniper,
ServiceNow (既存), Salesforce (既存),
Splunk, Dynatrace, New Relic, AppDynamics,
Intune, SCCM, Active Directory, Entra ID,
Copilot, ChatGPT, Dify, LangChain

### Tier3: 今回は追加しない（抽象カテゴリ）
クラウド, ネットワーク, RDBMS, ETL, DWH, AI, セキュリティ, インフラ基盤
→ 偽陽性リスクが高いため保留。fuzzy_matchで十分カバーされる。

## 変更2: 短縮alias厳格ルール

skill_aliases.jsonに `strict_aliases` フラグを追加:
```json
{
  "aliases": {
    "nw": {"canonical": "ネットワーク", "strict": true},
    "oci": {"canonical": "OCI", "strict": true},
    "bi": {"canonical": "Power BI", "strict": true},
    "ad": {"canonical": "Active Directory", "strict": true}
  }
}
```
- strict=true: 完全一致（前後に単語境界必須）でのみマッチ
- strict=false（デフォルト）: 部分一致可

SkillNormalizer.normalize_hard()で、strict aliasは以下の条件でのみマッチ:
```python
if alias_entry.get("strict"):
    # 入力文字列がalias完全一致の場合のみ
    if input_lower == alias_key:
        return canonical
else:
    # 既存の部分一致ロジック
    ...
```

## 変更3: process_skill別軸保存

matcher.py の judge() で、_partition_required_skills() が返す competencies を:
- スキル判定からは除外（現行通り）
- 結果JSONに `process_requirements` として保存
```python
result = {
    "verdict": verdict,
    "reasons": reasons,
    "process_requirements": competencies,  # NEW
}
```

process_skillセット（178語から安全な80語を選定）:
```python
PROCESS_SKILLS = {
    "要件定義", "基本設計", "詳細設計", "製造", "単体テスト", "結合テスト",
    "総合テスト", "システムテスト", "受入テスト", "運用テスト",
    "テスト設計", "テスト実施", "リリース", "デプロイ",
    "進捗管理", "課題管理", "品質管理", "変更管理", "構成管理",
    "障害対応", "障害切り分け", "インシデント対応",
    "上流工程", "下流工程", "要件ヒアリング",
    "ER設計", "DB設計", "画面設計", "API設計", "IF設計",
    # ... 合計80語程度
}
```

## テスト
1. 既存43テスト全合格
2. Tier1/2の新スキル normalize_hard() テスト（代表20語）
3. strict alias テスト（NW, OCI等が誤爆しないこと）
4. process_requirements が結果JSONに含まれること
5. 親子重複テスト（React/React Native が二重カウントしないこと）

## 禁止事項
- Tier3（抽象語）を追加しない
- 既存aliasを削除/変更しない
- NG判定ロジックを緩めない
