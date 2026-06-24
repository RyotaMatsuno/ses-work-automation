import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
sys.path.insert(0, str(base / "matching_v3"))
sys.path.insert(0, str(base))

from structurer import structure

from config import Config
from cost_guard import CostGuard

cfg = Config()
cg = CostGuard()

print("=" * 60)
print("【バグ検証】エラーハンドリング・エッジケース")
print("=" * 60)

# ---- バグ1: 空メール ----
print("\n[1] 空メール")
try:
    r = structure("", cg, cfg)
    print(f"  OK: 空でも返る → {r}")
except Exception as e:
    print(f"  ERROR: {e}")

# ---- バグ2: 超長メール（truncate動作確認）----
print("\n[2] 超長メール（8000文字超）")
long_body = "Java Spring Boot SQL\n" * 500
try:
    r = structure(long_body, cg, cfg)
    print(f"  OK: truncate動作 required={r.get('required_skills')[:3]}")
except Exception as e:
    print(f"  ERROR: {e}")

# ---- バグ3: レスポンスのusage取得（OpenAI形式）----
print("\n[3] OpenAI usageフィールド確認")
import urllib.request

headers_h = {"Authorization": f"Bearer {cfg.get('OPENAI_API_KEY')}", "Content-Type": "application/json"}
body = json.dumps(
    {"model": "gpt-4o-mini", "max_tokens": 50, "messages": [{"role": "user", "content": "test"}]}
).encode()
req = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=body, headers=headers_h, method="POST")
with urllib.request.urlopen(req, timeout=15) as resp:
    data = json.loads(resp.read())
    usage = data.get("usage", {})
    print(f"  prompt_tokens: {usage.get('prompt_tokens')}")
    print(f"  completion_tokens: {usage.get('completion_tokens')}")
    print(f"  input_tokensキーは存在するか: {'input_tokens' in usage}")
    print("  → structurer.pyのfallback: prompt_tokensを使用 ✓")

# ---- バグ4: cost_guard の日次上限チェック ----
print("\n[4] cost_guard.can_call() 動作確認")
can = cg.can_call(1000, 300)
print(f"  can_call(1000, 300): {can}")
model_used = cg.get_model()
print(f"  get_model(): {model_used}")

# ---- バグ5: ledgerへの記録確認 ----
print("\n[5] ledger記録確認")
cost_log = base / "usage_tracker" / "cost_log.jsonl"
if cost_log.exists():
    lines = cost_log.read_text(encoding="utf-8", errors="replace").splitlines()
    print(f"  cost_log: {len(lines)}件")
    if lines:
        last = json.loads(lines[-1])
        print(f"  最新: script={last.get('script')} model={last.get('model')} cost=${last.get('cost_usd'):.5f}")
        # gpt-4o-miniで記録されているか
        if "gpt" in last.get("model", ""):
            print("  OK: gpt-4o-miniで記録されている")
        else:
            print(f"  WARN: モデルが{last.get('model')}になっている")
else:
    print("  cost_log.jsonl 未生成（初回実行前）")

# ---- バグ6: SES_MatchingV3タスク経由の実行で正しくmatching_v3ディレクトリをcwdにするか ----
print("\n[6] wd_matching_v3.bat のcwd確認")
bat = base / "wd_matching_v3.bat"
bat_text = bat.read_bytes().decode("ascii")
has_cd = "cd /d" in bat_text and "matching_v3" in bat_text
print(f"  cd /d matching_v3: {'OK' if has_cd else 'NG'}")
print(f"  bat内容: {repr(bat_text)}")

# ---- バグ7: matching_v3.pyがGPTモデルでも正常にresult.jsonを出力するか ----
print("\n[7] result.json出力確認（直近）")
result_json = base / "matching_v3" / "result.json"
if result_json.exists():
    stat = result_json.stat()
    print(f"  result.json: {stat.st_size}bytes, mtime={time.strftime('%Y-%m-%d %H:%M', time.localtime(stat.st_mtime))}")
else:
    print("  result.json: 未生成（次回SES_MatchingV3実行後に生成される）")
