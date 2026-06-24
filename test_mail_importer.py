import os
import subprocess
import sys

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

# mail_attachment_importer の importer.py を dry-run テスト
result = subprocess.run(
    [sys.executable, "mail_attachment_importer/importer.py", "--dry-run", "--limit", "1"],
    capture_output=True,
    cwd=base,
    timeout=60,
)
out = result.stdout.decode("utf-8", errors="replace")
err = result.stderr.decode("utf-8", errors="replace")

with open(os.path.join(base, "mail_importer_test.txt"), "w", encoding="utf-8") as f:
    f.write(f"RC: {result.returncode}\n\n=== STDOUT ===\n{out}\n=== STDERR ===\n{err}")

print("RC:", result.returncode, "stdout:", len(out), "stderr:", len(err))
