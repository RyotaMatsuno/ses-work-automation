import subprocess
import sys

SRC = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(SRC, "rb") as f:
    raw = f.read()
text = raw.decode("utf-8", errors="replace")

# engineer_query 内の skill_match チェック直後に、
# スキル空案件の gross >= 10 条件を追加
old = (
    "            if not skill_match(required, engineer_skills):\n"
    "                continue\n"
    "            budget = _number_prop(project, PROP_RATE)"
)
new = (
    "            if not skill_match(required, engineer_skills):\n"
    "                continue\n"
    "            budget = _number_prop(project, PROP_RATE)\n"
    "            if not required and budget < 80:\n"  # スキル指定なし案件は単価80万未満を除外
    "                continue"
)
# ↑実は粗利で弾く方がシンプル。budgetフィルタでなく、skill空 AND gross < 10 を除外

old2 = (
    "            if not skill_match(required, engineer_skills):\n"
    "                continue\n"
    "            budget = _number_prop(project, PROP_RATE)"
)
new2 = (
    "            # skill empty check: require higher gross for unspecified skills\n"
    "            if not skill_match(required, engineer_skills):\n"
    "                continue\n"
    "            budget = _number_prop(project, PROP_RATE)"
)

# 代わりにgross計算後に条件追加
old3 = (
    "            gross  = calc_gross_profit(budget, engineer_rate)\n"
    "            if gross < _gross_threshold(_select_prop(project, PROP_ASSIGNEE)):\n"
    "                continue"
)
new3 = (
    "            gross  = calc_gross_profit(budget, engineer_rate)\n"
    "            _thresh = _gross_threshold(_select_prop(project, PROP_ASSIGNEE))\n"
    "            # skill-empty projects need gross>=10 to reduce noise\n"
    "            if not required and gross < 10:\n"
    "                continue\n"
    "            if gross < _thresh:\n"
    "                continue"
)

if old3 in text:
    text = text.replace(old3, new3, 1)
    sys.stdout.buffer.write(b"skill-empty gross filter added\n")
else:
    sys.stdout.buffer.write(b"target not found\n")

with open(SRC, "w", encoding="utf-8") as f:
    f.write(text)

result = subprocess.run(
    ["python", "-m", "py_compile", SRC], capture_output=True, text=True, encoding="utf-8", errors="replace"
)
sys.stdout.buffer.write(f"Syntax: {'OK' if result.returncode == 0 else result.stderr}\n".encode())
