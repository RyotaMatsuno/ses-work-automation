import glob
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
out = []


def w(*a):
    out.append(" ".join(str(x) for x in a))


# 1. py_compile result Codex wrote
w("=== py_compile result ===")
for p in glob.glob(os.path.join(BASE, "**", "*py_compile_result*.txt"), recursive=True):
    w(f"[{p.replace(BASE, '')}]")
    w(open(p, encoding="utf-8", errors="replace").read()[:600])

# 2. git diff --stat (scope check: confirm NO send files touched)
w("\n=== git diff --stat ===")
r = subprocess.run(
    ["git", "-C", BASE, "diff", "--stat"], capture_output=True, text=True, encoding="utf-8", errors="replace"
)
w(r.stdout[-1500:] or r.stderr[:300])
w("\n=== git status --short ===")
r = subprocess.run(
    ["git", "-C", BASE, "status", "--short"], capture_output=True, text=True, encoding="utf-8", errors="replace"
)
w(r.stdout[-1500:] or "(clean)")

# 3. model_config.py contents
w("\n=== common/model_config.py ===")
mc = os.path.join(BASE, "common", "model_config.py")
if os.path.exists(mc):
    w(open(mc, encoding="utf-8", errors="replace").read()[:900])
else:
    w("NOT FOUND")

# 4. hardcoded model strings outside model_config.py (active, non-comment)
w("\n=== hardcoded claude-/gpt- in production (excl model_config, tests, _archive, patch_*) ===")
for p in glob.glob(os.path.join(BASE, "**", "*.py"), recursive=True):
    rel = p.replace(BASE, "")
    if any(
        s in rel
        for s in [
            "model_config",
            "_archive",
            "test",
            "patch_",
            "rewrite_",
            "build_importer",
            "write_",
            "_audit",
            "fix_",
            "add_",
            "check_",
            "diagnose",
            "poc_",
            "consult_",
            "validate_",
            "cost_estimate",
            "cost_calculator",
            "ledger.py",
        ]
    ):
        continue
    try:
        t = open(p, encoding="utf-8", errors="replace").read()
    except:
        continue
    for i, l in enumerate(t.splitlines(), 1):
        s = l.strip()
        if s.startswith("#"):
            continue
        if ('"claude-' in l or "'claude-" in l or '"gpt-' in l or "'gpt-" in l) and "model" in l.lower():
            w(f"  {rel}:{i}: {s[:110]}")

# 5. skill_judge fallback: sonnet gone?
w("\n=== skill_judge.py _select_fallback_model (now) ===")
sj = os.path.join(BASE, "matching_v2", "skill_judge.py")
lines = open(sj, encoding="utf-8", errors="replace").read().splitlines()
grab = False
for i, l in enumerate(lines, 1):
    if "_select_fallback_model" in l:
        grab = True
    if grab:
        w(f"  {i}: {l.rstrip()[:120]}")
        if (
            i > 0
            and "return" in l
            and grab
            and l.strip().startswith("return")
            and i > [j for j, x in enumerate(lines, 1) if "_select_fallback_model" in x][0] + 2
        ):
            pass
    if grab and l.strip() == "" and i > [j for j, x in enumerate(lines, 1) if "_select_fallback_model" in x][0] + 6:
        break

# 6. confirm ledger guard wired in the 3 scripts
w("\n=== ledger guard presence ===")
for rel in ["mail_pipeline/mail_pipeline.py", "skill_reader/skill_reader.py", "outlook/outlook_to_notion.py"]:
    p = os.path.join(BASE, rel)
    t = open(p, encoding="utf-8", errors="replace").read() if os.path.exists(p) else ""
    w(
        f"  {rel}: ledger_can_spend={'YES' if 'ledger_can_spend' in t else 'NO'} / VISION_MODEL={'YES' if 'VISION_MODEL' in t else '-'} / TEXT_MODEL={'YES' if 'TEXT_MODEL' in t else '-'}"
    )

# 7. codex still running?
tl = subprocess.run(["tasklist"], capture_output=True, text=True, errors="replace").stdout
w("\n=== codex/node procs ===")
w("node.exe present:", "node.exe" in tl)

with open(os.path.join(BASE, "_verify_phase1.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("DONE")
