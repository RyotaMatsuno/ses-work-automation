import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3"
out = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\phase_e_verify.txt"

snippets = {}
# cost_guard.py の上限値
with open(base + r"\cost_guard.py", encoding="utf-8") as f:
    cg = f.read()
snippets["cost_guard_limits"] = "\n".join(
    [l for l in cg.splitlines() if any(x in l for x in ["DAILY_COST", "MONTHLY_", "LLM_INPUT", "LLM_OUTPUT", "HAIKU"])]
)

# structurer.py のOpenAI部分
with open(base + r"\structurer.py", encoding="utf-8") as f:
    st = f.read()
oi_start = st.find("def _call_openai")
oi_end = st.find("\ndef ", oi_start + 1)
snippets["structurer_openai_fn"] = st[oi_start:oi_end]

# matcher.py のjudge末尾
with open(base + r"\matcher.py", encoding="utf-8") as f:
    mt = f.read()
snippets["matcher_price_check"] = mt[mt.find("eng_price") : mt.find("required_raw")]
snippets["matcher_eng_skills"] = mt[mt.find("required_raw") : mt.find("for skill in required_raw") + 50]
snippets["matcher_ambig_end"] = mt[mt.find("non_ambig") :]

combined = "\n\n".join(f"=== {k} ===\n{v}" for k, v in snippets.items())
with open(out, "w", encoding="utf-8") as f:
    f.write(combined)
print(combined)
