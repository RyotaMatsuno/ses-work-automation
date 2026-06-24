import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = os.getcwd()
gc_dir = os.path.join(SES, "gate_checker")

# prompts/ 全ファイル
print("■ prompts/ ファイル一覧と内容")
prompts_dir = os.path.join(gc_dir, "prompts")
if os.path.isdir(prompts_dir):
    for fn in sorted(os.listdir(prompts_dir)):
        fp = os.path.join(prompts_dir, fn)
        if os.path.isfile(fp):
            sz = os.path.getsize(fp)
            print(f"\n--- {fn} ({sz}b) ---")
            with open(fp, encoding="utf-8", errors="replace") as f:
                print(f.read())
else:
    print("  prompts/ 未存在")

# TASKS.md 現状
print("\n■ gate_checker/TASKS.md 内容")
tasks = os.path.join(gc_dir, "TASKS.md")
if os.path.exists(tasks):
    with open(tasks, encoding="utf-8", errors="replace") as f:
        print(f.read())

# results/ 直近ファイル
print("\n■ results/ 直近3件")
results_dir = os.path.join(gc_dir, "results")
if os.path.isdir(results_dir):
    import glob

    rfiles = sorted(glob.glob(os.path.join(results_dir, "*.json")), key=os.path.getmtime, reverse=True)[:3]
    for rf in rfiles:
        sz = os.path.getsize(rf)
        print(f"\n--- {os.path.basename(rf)} ({sz}b) ---")
        with open(rf, encoding="utf-8", errors="replace") as f:
            import json

            data = json.load(f)
        # review_text は長いので省略
        data_display = {k: (v[:200] + "..." if isinstance(v, str) and len(v) > 200 else v) for k, v in data.items()}
        print(json.dumps(data_display, ensure_ascii=False, indent=2))
else:
    print("  results/ 未存在")
