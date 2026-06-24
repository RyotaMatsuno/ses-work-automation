import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
out = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\deploy_status.txt"

# Cloud Runの現在のリビジョンを確認
r = subprocess.run(
    'gcloud run revisions list --service=line-webhook --region=asia-northeast1 --limit=3 --format="table(name,status.conditions[0].status,createTime)"',
    shell=True,
    capture_output=True,
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
)
rev_out = r.stdout.decode("utf-8", errors="replace") + r.stderr.decode("utf-8", errors="replace")

# git log で最近のコミット
r2 = subprocess.run(
    "git log --oneline -5", shell=True, capture_output=True, cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
)
git_out = r2.stdout.decode("utf-8", errors="replace")

result = f"=== Cloud Run revisions ===\n{rev_out}\n=== git log ===\n{git_out}"
with open(out, "w", encoding="utf-8") as f:
    f.write(result)
print(result)
