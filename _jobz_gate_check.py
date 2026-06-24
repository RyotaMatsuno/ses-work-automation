import os
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = os.getcwd()

# .env からAPIキー読み込み
from pathlib import Path

env_path = Path(SES) / "config" / ".env"
config = {}
if env_path.exists():
    with open(env_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                config[k.strip()] = v.strip()

OPENAI_KEY = config.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
if not OPENAI_KEY:
    print("ERROR: OPENAI_API_KEY が見つかりません")
    sys.exit(1)

# ゲートレビュー内容
spec = r"""
【ゲート②：実装レビュー依頼】
システム: mail_pipeline (ses_work/mail_pipeline/mail_pipeline.py)

■ 発見した障害
run_pipeline.bat が `cd mail_pipeline/` した状態で `python mail_pipeline.py` を実行すると、
mail_pipeline.py 内の `from mail_pipeline.validation import ...` が自己参照になり
ModuleNotFoundError が発生する。

■ 現在のコード状況
- mail_pipeline.py L34: sys.path.insert(0, str(Path(__file__).parent.parent))  # ses_workをpathに追加
- mail_pipeline.py L36: from mail_pipeline.validation import (...)
- run_pipeline.bat: cd /d "%~dp0mail_pipeline" → python mail_pipeline.py

■ 提案する修正方針
【方法A】run_pipeline.bat を修正し、ses_work/ から実行する形に変更
  変更後: cd /d "%~dp0" (ses_work/) → python mail_pipeline\mail_pipeline.py

【方法B】mail_pipeline.py の import を相対importに変更
  from mail_pipeline.validation → from .validation (ただし __main__ 実行では使えない)

【方法C】mail_pipeline.py 冒頭の sys.path 設定後に from validation import に変更

■ レビュー観点
1. 3つの修正方法それぞれのリスク・副作用を評価せよ
2. 最も安全な修正方法を1つ推奨せよ
3. 修正後に他のimport（common, skill_reader, usage_tracker）が壊れないか確認せよ
4. GO / NG を明確に返せ

現在のsys.path設定:
  L34: sys.path.insert(0, str(Path(__file__).parent.parent))  # = ses_work/
  
これにより ses_work/ がpathに入るので:
  from mail_pipeline.validation import → mail_pipeline がパッケージとして認識される "はず"
  だが、実行時のcwdが mail_pipeline/ の場合、Pythonが mail_pipeline をカレントディレクトリと混同している可能性がある。
"""

headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
payload = {
    "model": "gpt-4o",
    "messages": [
        {
            "role": "system",
            "content": "あなたはPythonのimport構造とWindowsバッチ実行環境の専門家です。提示された問題を分析し、最適な修正方法をGO/NGで判定してください。日本語で回答してください。",
        },
        {"role": "user", "content": spec},
    ],
    "max_tokens": 1000,
    "temperature": 0,
}

print("■ GPT-4o ゲート②レビュー送信中...")
r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=60)
r.raise_for_status()
result = r.json()
review = result["choices"][0]["message"]["content"]
print("\n■ GPT-4o レビュー結果:")
print(review)
print(f"\n■ トークン使用量: {result['usage']}")
