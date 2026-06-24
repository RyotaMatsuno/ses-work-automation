import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")

# ========== 1. structurer.py: OpenAI対応追加 ==========
st_path = base / "matching_v3" / "structurer.py"
text = st_path.read_text(encoding="utf-8", errors="replace")

# _call_anthropic の直後に _call_openai を追加 + structurize()の振り分け修正
old_call_anthropic = """def _call_anthropic(prompt_text: str, model: str, config: Config):
    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError("anthropic package is required") from exc
    api_key = config.anthropic_api_key
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is required")
    client = anthropic.Anthropic(api_key=api_key)
    return client.messages.create(
        model=model,
        max_tokens=2000,
        temperature=0,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt_text}],
    )"""

new_call_funcs = """def _call_anthropic(prompt_text: str, model: str, config: Config):
    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError("anthropic package is required") from exc
    api_key = config.anthropic_api_key
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is required")
    client = anthropic.Anthropic(api_key=api_key)
    return client.messages.create(
        model=model,
        max_tokens=2000,
        temperature=0,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt_text}],
    )


def _call_openai(prompt_text: str, model: str, config: Config):
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("openai package is required: pip install openai") from exc
    api_key = config.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required")
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        max_tokens=2000,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text},
        ],
    )
    return resp"""

if old_call_anthropic in text:
    text = text.replace(old_call_anthropic, new_call_funcs)
    print("OK: _call_openai 追加")
else:
    print("NG: _call_anthropic 置換対象見つからない")
    sys.exit(1)

# _response_text でOpenAIレスポンスにも対応
old_response_text = """def _response_text(response: Any) -> str:"""
# 現在の_response_text全体を確認してから修正
lines = text.splitlines()
rt_start = next((i for i, l in enumerate(lines) if "def _response_text" in l), None)
print(f"_response_text: Line {rt_start + 1}")
for l in lines[rt_start : rt_start + 10]:
    print(f"  {l}")

# _response_textをAnthropicとOpenAIどちらにも対応させる
old_rt_block = None
for i, l in enumerate(lines):
    if "def _response_text" in l:
        # 関数全体を取得
        func_lines = []
        for j in range(i, len(lines)):
            func_lines.append(lines[j])
            if j > i and lines[j].strip().startswith("def "):
                func_lines = func_lines[:-1]
                break
        old_rt_block = "\n".join(func_lines)
        break

print(f"\n現在の_response_text:\n{old_rt_block}")
