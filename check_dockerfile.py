# -*- coding: utf-8 -*-
# Cloud Run上のline_query.pyのTOP_LIMITを確認するテストリクエスト
# webhook_server.pyに/debugエンドポイントがないので、
# ローカルのDockerfileとソースを確認する


# Dockerfileを確認
dockerfile_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\Dockerfile"
with open(dockerfile_path, encoding="utf-8") as f:
    print("=== Dockerfile ===", flush=True)
    print(f.read(), flush=True)
