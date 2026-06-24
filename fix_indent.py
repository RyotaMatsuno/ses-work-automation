import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
st_path = base / "matching_v3" / "structurer.py"
lines = st_path.read_text(encoding="utf-8", errors="replace").splitlines()

# Line 48-52を正しいインデント（4スペース）に修正
fixed_lines = []
for i, l in enumerate(lines, 1):
    if i == 48:
        fixed_lines.append("    # [GPT切替] モデル名でAnthropicとOpenAIを振り分け")
    elif i == 49:
        fixed_lines.append('    if model.startswith("gpt-") or model.startswith("o1") or model.startswith("o3"):')
    elif i == 50:
        fixed_lines.append("        response = _call_openai(prompt_text, model, cfg)")
    elif i == 51:
        fixed_lines.append("    else:")
    elif i == 52:
        fixed_lines.append("        response = _call_anthropic(prompt_text, model, cfg)")
    else:
        fixed_lines.append(l)

st_path.write_text("\n".join(fixed_lines) + "\n", encoding="utf-8")
print("OK: インデント修正")

# usageトークン取得もOpenAIに対応（Line 53付近）
# OpenAI: response.usage.prompt_tokens / completion_tokens
# Anthropic: response.usage.input_tokens / output_tokens
text = st_path.read_text(encoding="utf-8", errors="replace")
old_usage = (
    '    input_tokens = int(getattr(getattr(response, "usage", None), "input_tokens", est_input_tokens))\n'
    '    output_tokens = int(getattr(getattr(response, "usage", None), "output_tokens", est_output_tokens))'
)
new_usage = (
    '    usage = getattr(response, "usage", None)\n'
    "    # OpenAI: prompt_tokens/completion_tokens, Anthropic: input_tokens/output_tokens\n"
    "    input_tokens = int(\n"
    '        getattr(usage, "prompt_tokens", None)\n'
    '        or getattr(usage, "input_tokens", None)\n'
    "        or est_input_tokens\n"
    "    )\n"
    "    output_tokens = int(\n"
    '        getattr(usage, "completion_tokens", None)\n'
    '        or getattr(usage, "output_tokens", None)\n'
    "        or est_output_tokens\n"
    "    )"
)
if old_usage in text:
    text = text.replace(old_usage, new_usage)
    st_path.write_text(text, encoding="utf-8")
    print("OK: usage token取得 OpenAI/Anthropic両対応")
else:
    print("NG: usage置換対象見つからない（行確認）")
    for i, l in enumerate(text.splitlines(), 1):
        if "input_tokens" in l and "getattr" in l:
            print(f"  Line {i}: {repr(l)}")

# syntax確認
import subprocess

r = subprocess.run(
    ["python", "-c", "import py_compile; py_compile.compile('matching_v3/structurer.py', doraise=True); print('OK')"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=str(base),
)
print(f"syntax: {r.stdout.strip() or r.stderr.strip()[:100]}")
