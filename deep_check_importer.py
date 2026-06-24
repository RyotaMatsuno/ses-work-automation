import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

IMP = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_attachment_importer"
SES = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

# 1. SUPPORTED_EXTSにpptx/csv追加されているか確認
with open(os.path.join(IMP, "mail_fetcher.py"), encoding="utf-8") as f:
    mf = f.read()
print("=== mail_fetcher.py SUPPORTED_EXTS ===")
for line in mf.split("\n"):
    if "SUPPORTED_EXTS" in line or "pptx" in line or "csv" in line:
        print(" ", repr(line))

# 2. file_parser.pyの実際の拡張子チェック
with open(os.path.join(IMP, "file_parser.py"), encoding="utf-8") as f:
    fp = f.read()
print("\n=== file_parser.py parse_file分岐 ===")
in_parse_file = False
for line in fp.split("\n"):
    if "def parse_file" in line:
        in_parse_file = True
    if in_parse_file:
        print(" ", repr(line))
    if in_parse_file and line.strip() == "return None":
        break

# 3. importer.pyのテキスト長チェック閾値
print("\n=== importer.py テキスト長チェック ===")
for line in mf_content.split("\n") if False else []:
    pass
with open(os.path.join(IMP, "importer.py"), encoding="utf-8") as f:
    imp = f.read()
for line in imp.split("\n"):
    if "200" in line or "len(text" in line or "strip()" in line:
        print(" ", repr(line))

# 4. processed_ids.jsonの現状確認
pid_path = os.path.join(IMP, "processed_ids.json")
import json

with open(pid_path, encoding="utf-8") as f:
    pids = json.load(f)
if isinstance(pids, dict):
    for k, v in pids.items():
        print(f"processed_ids/{k}: {len(v)}件")
else:
    print(f"processed_ids: {len(pids)}件（list形式）")

# 5. DRY_RUNで実際の接続テスト
print("\n=== DRY_RUN接続テスト ===")
r = subprocess.run(
    [sys.executable, "importer.py"],
    capture_output=True,
    encoding="utf-8",
    errors="replace",
    cwd=IMP,
    env={**os.environ, "DRY_RUN": "1"},
    timeout=45,
)
out = r.stdout[-800:] if len(r.stdout) > 800 else r.stdout
err = r.stderr[-300:] if r.stderr else ""
print(out)
if err:
    print("STDERR:", err)
