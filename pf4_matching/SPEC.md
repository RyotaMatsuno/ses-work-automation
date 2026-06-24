# SPEC.md - Phase4: matching_v3品質修正

## 変更1: matching_v3.py — sys.path修正

matching_v3.pyの先頭（importより前）に追加:
```python
import sys as _sys
from pathlib import Path as _Path
_SES_WORK = str(_Path(__file__).resolve().parent.parent)
if _SES_WORK not in _sys.path:
    _sys.path.insert(0, _SES_WORK)
```
これにより `from common.ledger import ...` が scheduler実行時でも動く。

## 変更2: matcher.py — judge()の粗利ルール修正

現在:
```python
eng_price = float(engineer.get("単価（万円）") or 0)
case_max = float(case_json.get("price_max") or 0)
if case_max > 0 and eng_price > case_max + 15:
    return "NG", [...]
```
↓ 変更後（粗利5万床 + 上振れ制限）:
```python
eng_price = float(engineer.get("単価（万円）") or 0)
case_max = float(case_json.get("price_max") or 0)
if case_max > 0 and eng_price > 0:
    gross = case_max - eng_price
    if gross < 5.0:   # 粗利5万未満はNG（逆ザヤ・マイナス含む）
        return "NG", [f"粗利不足: 案件{case_max}万-エンジニア{eng_price}万={gross}万 (最低5万必要)"]
```

## 変更3: matcher.py — 未知必須スキルをREVIEW要因に

現在: `normalize(skill)` がNoneなら判定スキップ（黙殺）

変更後:
```python
for skill in required_raw:
    normalized = normalizer.normalize(skill)
    if normalized is None:
        # エイリアス未登録の必須スキル → REVIEW要因（黙殺しない）
        reasons.append(f"未登録必須スキル要確認: {skill}")
    elif normalized not in eng_skills:
        missing.append(normalized)
if missing:
    return "NG", [f"必須スキル不足: {missing}"]
```
※ missing（登録済み必須スキル不足）はNGのまま。未知スキルはREVIEW扱い。

## 変更4: matcher.py — 並行スコア超過をNGに

現在: p_score >= 5.0 → reasons.append (REVIEW扱い)
変更後:
```python
p_score = _calc_parallel_score(engineer)
if p_score >= 5.0:
    return "NG", [f"並行過多: スコア{p_score:.1f}（上限5.0）"]
```
※ この行はrequired_skillsチェックの後に置く

## 変更5: notion_client.py — get_active_engineers()に提案対象フラグfilter追加

`get_active_engineers()` の payload の filter["and"] 配列に追加:
```python
{"property": "提案対象フラグ", "checkbox": {"equals": True}}
```
ただし、Notionのプロパティ名が違う場合に備え、エラー時は元のfilterで再試行するのではなく
そのままフィルタを追加した状態で実行すること（Notion APIはunknown propertyを400で返す）。
※ DB上の正確なプロパティ名が"提案対象フラグ"であることは監査で確認済み。

## 変更6: matching_v3/cost_guard.py — Geminiデグレードパスを除去

現在の `get_model()`:
```python
def get_model(self) -> str:
    monthly = self._get_monthly_cost()
    if monthly >= self.MONTHLY_DEGRADE_USD:
        return os.environ.get("FALLBACK_MODEL", "gemini-2.0-flash")
    return os.environ.get("STRUCTURER_MODEL", "claude-haiku-4-5-20251001")
```
↓ 変更後（Gemini劣化を廃止、常にHaiku。月次ハード上限はcan_callで対処）:
```python
def get_model(self) -> str:
    return os.environ.get("STRUCTURER_MODEL", DEFAULT_STRUCTURER_MODEL)
```
`MONTHLY_DEGRADE_USD` 定数はそのまま残してよい（uses them in can_call）。
`can_call()` は既に `if self._get_monthly_cost() >= self.MONTHLY_STOP_USD: return False` があるのでそれで止まる。

## 変更7: SES_MatchingV3タスクのWorking Directory を ses_work に設定

`pf4_matching/setup_workdir.py` を新規作成・実行:
```python
import subprocess
SES_WORK = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work'
cmd = ['powershell', '-NoProfile', '-Command',
    f'$t = Get-ScheduledTask -TaskName SES_MatchingV3; '
    f'$t.Actions[0].WorkingDirectory = "{SES_WORK}"; '
    f'Set-ScheduledTask -TaskName SES_MatchingV3 -Action $t.Actions']
result = subprocess.run(cmd, capture_output=True, text=True)
print("returncode:", result.returncode)
print(result.stdout[:200])
print(result.stderr[:200])
```
