import subprocess

# Cloud Run の Cloud Build トリガーが設定されているか確認
result = subprocess.run(
    ["cmd", "/c", "gcloud", "builds", "triggers", "list", "--format=value(name,github.push.branch)"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
)
print("Build triggers:", result.stdout[:500])
print("stderr:", result.stderr[:300])
