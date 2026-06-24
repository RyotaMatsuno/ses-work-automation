import os
import sys
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = Path(os.getcwd())
env = {}
with open(SES / "config" / ".env", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()

OPENAI_KEY = env.get("OPENAI_API_KEY", "")

# 修正後のコードを読む
rfu = (SES / "flag_auto_updater" / "run_flag_updater.py").read_text(encoding="utf-8")
mv3 = (SES / "matching_v3" / "matching_v3.py").read_text(encoding="utf-8")


# _setup_logging 部分だけ抽出
def extract_func(code, func_name):
    lines = code.split("\n")
    out, in_func, count = [], False, 0
    for i, line in enumerate(lines, 1):
        if f"def {func_name}" in line:
            in_func = True
        if in_func:
            out.append(f"L{i}: {line}")
            count += 1
        if in_func and count > 5 and line.strip().startswith("def ") and func_name not in line:
            break
    return "\n".join(out)


rfu_func = extract_func(rfu, "_setup_logging")
mv3_func = extract_func(mv3, "_setup_logging")

review_request = f"""
【ゲート②：コードレビュー依頼】
システム: matching_v3 / flag_auto_updater の logging 修正
修正者: ジョブズ（直接実装 ※本来はCursor経由すべきだったが緊急対応）

■ 修正の背景
matching_v3.py から flag_auto_updater.run_flag_updater() を呼び出すと、
run_flag_updater の _setup_logging() が basicConfig(force=True) でルートロガーを
上書きしていたため、matching_v3 のログが全て flag_updater_YYYYMMDD.log に流れ、
matching_v3_YYYYMMDD.log が永久に空になっていた。

■ 修正① flag_auto_updater/run_flag_updater.py
{rfu_func}

修正内容:
- force=True を削除
- 既にrootロガーにhandlerが存在する場合（＝親から呼ばれた場合）は
  flag_updater専用のFileHandlerだけ追加してreturn
- 単独起動時は従来通りbasicConfigで設定

■ 修正② matching_v3/matching_v3.py
{mv3_func}

修正内容:
- basicConfig に force=True を追加
- これにより matching_v3 が _setup_logging() を呼ぶと、
  flag_auto_updater が先にhandlerを設定していても必ず上書きする

■ 動作確認済み
- matching_v3_20260612.log に matching_v3 自身のWARNINGログが出力されることを確認
- flag_updater_20260612.log にも flag_auto_updater のログが出力されることを確認
- ProcessedDB で MATCH32件・REVIEW13件の正常処理を確認

■ レビュー観点
1. 修正①（force=True削除 + ハンドラー追加方式）に問題はないか
2. 修正②（matching_v3側でforce=True）に問題はないか
3. 両修正の組み合わせで意図通りに動作するか（ログの二重書き込みなど副作用がないか）
4. 単独起動・親から呼び出し両方のケースで正常に動くか
5. このまま本番運用して問題ないか

【判定: GO】または【判定: NG】で返してください。
"""

headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
payload = {
    "model": "gpt-4o",
    "messages": [
        {
            "role": "system",
            "content": "あなたはPythonのloggingモジュールの専門家です。提示されたコードと修正内容を正確に分析し、GO/NGで判定してください。日本語で回答してください。",
        },
        {"role": "user", "content": review_request},
    ],
    "max_tokens": 1000,
    "temperature": 0,
}

print("■ GPT-4o ゲート② 送信中...")
r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=60)
r.raise_for_status()
result = r.json()
print("\n■ GPT-4o ゲート② レビュー結果:")
print(result["choices"][0]["message"]["content"])
print(f"\n■ トークン: {result['usage']}")
