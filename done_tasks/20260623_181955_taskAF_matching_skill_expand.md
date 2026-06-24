# 【Cursor作業指示】Task AF: マッチング精度改善（スキル辞書拡張 + soft_aliases有効化）

対象ディレクトリ: ses_work/matching_v3/
作業内容: skill_aliases.jsonの拡張 + soft_aliases有効化 + 能力記述のREVIEW回避
参照ファイル: CLAUDE.md / skill_aliases.json / skill_judge.py / matcher.py
完了条件: REVIEW率75%→50%以下に改善（語彙外起因のREVIEWを半減）

---

## 背景
- 現在のREVIEW率: 75.5%（386/511候補者）
- REVIEW理由の96%: 「語彙外必須スキル要確認」
- skill_aliases.json: 31語のみ → 大多数のスキルがマッチ不能
- soft_aliases: 無効のまま

## 変更1: canonical skills追加（15語）

skill_aliases.jsonのaliases/canonical_skillsに以下を追加:

| canonical | aliases |
|---|---|
| SQL | sql, PL/SQL, pl/sql |
| Terraform | terraform, tf |
| CI/CD | ci/cd, ci, cd, 継続的インテグレーション |
| Windows | windows, win, windows環境 |
| Windows Server | windows server, winサーバ, winサーバー |
| Cisco | cisco |
| SAP | sap, s/4hana, s4hana |
| ServiceNow | servicenow |
| Salesforce | salesforce, sfdc |
| Datadog | datadog, データドッグ |
| FortiGate | fortigate, fortinet |
| 生成AI | 生成ai, generative ai, llm |
| Microsoft 365 | m365, ms365, microsoft365 |
| .NET | .net, dotnet, asp.net, vb.net |
| COBOL | cobol |

## 変更2: soft_aliases有効化

skill_aliases.jsonの`soft_aliases_enabled`を`true`に変更。
既存soft_aliasesはそのまま（.NET→C#, Rails→Ruby, CentOS→Linux, PL/SQL→Oracle等）。

ただし、soft_aliasesはスコア加点のみに使用し、確定一致（MATCH判定）には使わない。
skill_judge.pyで:
- hard_aliases: 完全一致 → MATCH判定に使用
- soft_aliases: 近似一致 → REVIEW判定のスコア加点のみ（MATCHにはしない）

## 変更3: 能力記述のREVIEW回避

以下のパターンは「語彙外必須スキル」として REVIEW に落とさず、スキップする:
```python
CAPABILITY_PATTERNS = [
    r".*経験$",           # 設計経験、運用経験、要件定義経験
    r".*経験者$",         # 保守運用経験者
    r".*できる.*",        # 基本設計自走できる人
    r".*可能.*",          # 対応可能な方
    r".*以上$",           # 3年以上
    r".*知識$",           # 基本知識
    r".*スキル$",         # コミュニケーションスキル
]
```
これらはスキル判定から除外し、別途competencyとしてログに記録する。

## テスト方法
- 6/23のmatched 98案件に対して再マッチング（dry-run）を実行
- REVIEW率が50%以下になることを確認
- MATCHだった案件がNGに変わっていないことを確認（回帰テスト）

## 禁止事項
- CostGuardなしでLLMを呼び出さない
- 既存のMATCH判定を壊さない（追加のみ、削除なし）
- エンジニアDBのスキルプロパティを変更しない
