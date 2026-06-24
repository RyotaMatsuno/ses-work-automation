import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

IMP = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_attachment_importer"
results = {}

# 構文チェック
for fn in ["ai_extractor.py", "notion_writer.py", "importer.py"]:
    r = subprocess.run([sys.executable, "-m", "py_compile", fn], capture_output=True, cwd=IMP)
    results[f"構文/{fn}"] = "OK" if r.returncode == 0 else f"NG: {r.stderr.decode('utf-8', 'replace')[:60]}"

# スキル数確認
with open(IMP + r"\ai_extractor.py", encoding="utf-8") as f:
    ai = f.read()
skill_count = ai.count('"', ai.find("SKILL_OPTIONS"), ai.find("]", ai.find("SKILL_OPTIONS"))) // 2
results[f"スキル種数({skill_count}種)"] = "OK" if skill_count > 40 else "NG"

# 重複チェック改善確認
with open(IMP + r"\notion_writer.py", encoding="utf-8") as f:
    nw = f.read()
results["重複チェック/_normalize_name"] = "OK" if "_normalize_name" in nw else "NG"
results["重複チェック/正規化一致"] = "OK" if "正規化一致" in nw else "NG"

# processed_ids確認
pid_path = IMP + r"\processed_ids.json"
with open(pid_path, encoding="utf-8") as f:
    pids = json.load(f)
size = os.path.getsize(pid_path)
results[f"processed_ids/sessales({len(pids['sessales'])}件)"] = "OK" if len(pids["sessales"]) <= 3000 else "NG"
results[f"processed_ids/サイズ({size // 1024}KB)"] = "OK" if size < 50000 else "NG"

# 自動トリム確認
with open(IMP + r"\importer.py", encoding="utf-8") as f:
    imp = f.read()
results["自動トリム/PROCESSED_IDS_KEEP"] = "OK" if "PROCESSED_IDS_KEEP" in imp else "NG"

print("=" * 55)
print("修正完了チェック結果")
print("=" * 55)
all_ok = True
for k, v in results.items():
    icon = "✅" if v == "OK" else "❌"
    if v != "OK":
        all_ok = False
    print(f"  {icon} {k}: {v}")
print("=" * 55)
print(f"  {'✅ 全項目クリア' if all_ok else '❌ 要確認あり'}")
