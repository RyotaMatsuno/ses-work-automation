import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
st_path = base / "matching_v3" / "structurer.py"
text = st_path.read_text(encoding="utf-8", errors="replace")

# _response_text: OpenAIレスポンスにも対応
old_rt = """def _response_text(response: Any) -> str:
    content = getattr(response, "content", [])
    parts: list[str] = []
    for item in content:
        text = getattr(item, "text", None)
        if text is None and isinstance(item, dict):
            text = item.get("text")
        if text:
            parts.append(text)
    return "".join(parts)"""

new_rt = """def _response_text(response: Any) -> str:
    # OpenAI ChatCompletion
    if hasattr(response, "choices"):
        return response.choices[0].message.content or ""
    # Anthropic Messages
    content = getattr(response, "content", [])
    parts: list[str] = []
    for item in content:
        text = getattr(item, "text", None)
        if text is None and isinstance(item, dict):
            text = item.get("text")
        if text:
            parts.append(text)
    return "".join(parts)"""

if old_rt in text:
    text = text.replace(old_rt, new_rt)
    print("OK: _response_text OpenAI対応追加")
else:
    print("NG: _response_text置換対象見つからない")
    sys.exit(1)

# structurize() のモデル振り分け修正
# 現在: _call_anthropic(prompt_text, model, cfg) を呼んでいる
old_structurize_call = "response = _call_anthropic(prompt_text, model, cfg)"
new_structurize_call = (
    "# [GPT切替] モデル名でAnthropicとOpenAIを振り分け\n"
    '        if model.startswith("gpt-") or model.startswith("o1") or model.startswith("o3"):\n'
    "            response = _call_openai(prompt_text, model, cfg)\n"
    "        else:\n"
    "            response = _call_anthropic(prompt_text, model, cfg)"
)

if old_structurize_call in text:
    text = text.replace(old_structurize_call, new_structurize_call)
    print("OK: structurize() 振り分け追加")
else:
    print("NG: structurize()呼び出し置換対象見つからない")
    # 現在の呼び出し行を確認
    for i, l in enumerate(text.splitlines(), 1):
        if "_call_anthropic" in l or "_call_openai" in l:
            print(f"  Line {i}: {l.strip()}")
    sys.exit(1)

# ファイル書き込み
st_path.write_text(text, encoding="utf-8")
print("OK: structurer.py 書き込み完了")
