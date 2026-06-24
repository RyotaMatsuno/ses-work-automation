# -*- coding: utf-8 -*-
# Dockerfileのtimeoutを60→120秒に変更
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\Dockerfile"
with open(path, encoding="utf-8") as f:
    content = f.read()

print("変更前:", flush=True)
print(content, flush=True)

new_content = content.replace("--timeout 60", "--timeout 120")
with open(path, "w", encoding="utf-8") as f:
    f.write(new_content)

print("\n変更後:", flush=True)
with open(path, encoding="utf-8") as f:
    print(f.read(), flush=True)
