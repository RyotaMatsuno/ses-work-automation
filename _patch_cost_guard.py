import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from datetime import datetime

# バックアップ
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = f"cost_guard.py.bak_{ts}"
shutil.copy("cost_guard.py", backup)
print(f"バックアップ: {backup}")

# 修正
with open("cost_guard.py", encoding="utf-8") as f:
    content = f.read()

old = """SOFT_DAILY_LIMIT = 0.8  # 2026-06-10: 日次ソフト上限を $1 に合わせて調整
HARD_DAILY_LIMIT = 1.5  # 2026-06-10: 最終砦（$1 超過時のCloud Run LLM_KILL）
MONTHLY_LIMIT = 6.0    # 2026-06-10: common/ledger.py と統一"""

new = """# 2026-06-12: 多層防御設計に変更
# レイヤー1 (common/ledger.py): 通常運用上限 $8/日・$140/月（.envから読む）
# レイヤー2 (cost_guard.py)   : 緊急停止ライン $20/日・$300/月（レイヤー1が破壊された場合の最終砦）
# SOFT_DAILY_LIMITは早期警告用（$8の50%）
SOFT_DAILY_LIMIT = 4.0   # ソフト警告：日次$4 (レイヤー1上限の50%)
HARD_DAILY_LIMIT = 20.0  # 緊急停止：日次$20 (Cloud Run LLM_KILL=1発動ライン)
MONTHLY_LIMIT    = 300.0 # 月次緊急停止：$300 (レイヤー1月次$140の約2倍が最終砦)"""

if old not in content:
    print("❌ 対象文字列が見つかりません")
    print("現状の該当箇所:")
    import re

    for m in re.finditer(r"(SOFT_DAILY_LIMIT|HARD_DAILY_LIMIT|MONTHLY_LIMIT)\s*=.*", content):
        print(f"  {m.group()}")
    sys.exit(1)

new_content = content.replace(old, new)
with open("cost_guard.py", "w", encoding="utf-8") as f:
    f.write(new_content)

# 構文チェック
import subprocess

result = subprocess.run(["python", "-m", "py_compile", "cost_guard.py"], capture_output=True, text=True)
if result.returncode == 0:
    print("✅ 構文OK")
else:
    print(f"❌ 構文エラー: {result.stderr}")
    # ロールバック
    shutil.copy(backup, "cost_guard.py")
    print("ロールバックしました")
    sys.exit(1)

# 修正後の値を確認
print()
print("=== 修正後の cost_guard.py 上限値 ===")
with open("cost_guard.py", encoding="utf-8") as f:
    new_cg = f.read()
import re

for m in re.finditer(r"(SOFT_DAILY_LIMIT|HARD_DAILY_LIMIT|MONTHLY_LIMIT)\s*=.*", new_cg):
    print(f"  {m.group()[:120]}")
