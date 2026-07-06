import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import os
from datetime import datetime

PENDING = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pending_tasks"
ts = datetime.now().strftime("%Y%m%d_%H%M%S")

task = """【Cursor作業指示】
対象ディレクトリ: ses_work/matching_v3/
作業内容: マッチング品質3点修正（OOV fail closed + 低品質ゲート + 辞書拡張/denylist）
参照ファイル: CLAUDE.md / matching_v3/ / research_results/GPT_WALLHIT_matching_quality.md
完了条件: 3修正完了 + 今日のデータで再マッチングdry-run + mass match(30件超)が0件

## 背景
マッチング結果45件を全件レビュー。3つの重大品質問題を発見:
1. 必須スキル全OOV時に全員REVIEW → 36-52件マッチ
2. 低品質案件(confidence<0.5)で毎回同じ13人マッチ
3. 非技術ワードがスキル扱い + 主要スキルが辞書にない

## 修正1: OOV fail closed（最優先）

matching_v3.py のスキルマッチング処理に以下のゲートを追加:

```
マッチング前チェック:
if 案件の extracted_required_skills が 1件以上ある
   AND normalized_technical_skills が 0件:
   → status = "UNMATCHABLE_SKILL_OOV"
   → return 0 candidates
   → reason = "全必須スキルが辞書外のためマッチング不可"
```

- 案件自体は案件DBに残す（削除しない）
- business_status = "ng" + ng_reason = "ALL_REQUIRED_SKILLS_OOV"
- daily_statsにoov_skip_countを追加記録

## 修正2: 低品質案件のマッチング除外

extraction_confidenceが低い案件をマッチング対象から除外:

```
if extraction_confidence < 0.5:
   → status = "UNMATCHABLE_LOW_QUALITY"
   → return 0 candidates
   → reason = "構造化品質不足のためマッチング不可"
```

- confidence = 0.25 のNEEDS_REVIEW案件が対象（これで同じ13人パターンが消える）
- confidence = None（旧データ）は除外しない（後方互換）

## 修正3: 辞書拡張 + denylist

### A. skill_aliases.json に追加（canonical + aliases）
以下を追加:
- C++ → aliases: ["c++", "C＋＋", "cpp", "C/C++"]
- Dynamics 365 → aliases: ["dynamics365", "dynamics 365", "D365"]
- WinActor → aliases: ["winactor", "win actor", "ウィンアクター"]
- Databricks → aliases: ["databricks"]
- Unreal Engine → aliases: ["unrealengine", "unreal engine", "UE4", "UE5"]
- Blueprint → aliases: ["blueprint"]（Unreal Engine文脈）
- Informatica → aliases: ["informatica", "informatica cdi", "informatica powercenter"]
- intra-mart → aliases: ["intra-mart", "intramart", "im-formadesigner"]
- New Relic → aliases: ["new relic", "newrelic"]
- ServiceNow → aliases: ["servicenow", "service now"]
- Power Automate → aliases: ["power automate", "microsoft power automate", "ms power automate"]
- SD-WAN → aliases: ["sd-wan", "sdwan"]
- SOC → aliases: ["soc", "soc運用"]
- JP1 → aliases: ["jp1"]
- PCセットアップ → aliases: ["pcセットアップ", "pc setup", "キッティング"]

### B. 非技術ワードdenylist
matching_v3/denylist.json を新規作成:
```json
{
  "task_words": ["課題", "課題解決", "課題解決能力", "課題管理"],
  "soft_traits": ["能動的行動", "勤怠安定性", "コミュニケーション能力", "自走力", "主体性"],
  "licenses": ["運転免許", "普通自動車免許"],
  "noise": ["案件", "経験", "実務経験", "業務経験"]
}
```

### C. validate_skill にdenylistチェック追加
```python
def validate_skill(skill_text):
    # 既存のバリデーション...
    
    # denylistチェック（新規追加）
    if skill_text.lower() in DENYLIST_FLAT:
        return False, "denylisted"
    
    # 括弧・記号を含むmalformed文字列の除去
    if re.search(r'[】【\[\]{}]', skill_text):
        return False, "malformed"
    
    # 既存のロジック...
```

### D. マッチング時のスキル分類
required_skillsの中で:
- TECH_SKILLのみをhard matchingの対象にする
- SOFT_TRAIT / LICENSE / TASK_WORDはマッチング判定に使わない（メタデータとして保持）

## テスト

### 再マッチング dry-run
今日のマッチ結果45件を対象に修正版で再マッチング:
```python
python matching_v3.py --dry-run --reprocess-today
```

### 検証項目
- [ ] mass match(30件超)が0件であること
- [ ] 「課題」「能動的行動」等がスキルフィルタに使われないこと
- [ ] C++/Dynamics365等の辞書追加スキルが正常にマッチすること
- [ ] confidence < 0.5 の案件がマッチング除外されること
- [ ] 全OOVスキル案件がマッチング除外されること
- [ ] 正常な案件（Azure基盤、AWS環境構築等）のマッチ結果が悪化しないこと

## 期待効果
- REVIEW率: 85% → 20%以下
- mass match(30+): 12件 → 0件
- 同じ13人パターン: 消滅
- avg matches: 10.6 → 3-5

## 禁止事項
- extractors/ のコード変更（R5で安定済み）
- Notion DBの既存データ変更
- CostGuardバイパス

## 完了条件チェックリスト
- [ ] OOV fail closed 実装
- [ ] 低品質ゲート 実装
- [ ] skill_aliases.json 15スキル追加
- [ ] denylist.json 作成 + validate_skill統合
- [ ] malformed文字列フィルタ追加
- [ ] dry-run実行 → mass match 0件確認
- [ ] 正常案件のマッチ結果が悪化していない確認
"""

fpath = os.path.join(PENDING, "08_" + ts + "_matching_quality_fix.md")
with open(fpath, 'w', encoding='utf-8') as f:
    f.write(task)

print("Created: " + os.path.basename(fpath))
