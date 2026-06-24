import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
st_path = base / "matching_v3" / "structurer.py"
text = st_path.read_text(encoding="utf-8", errors="replace")

# _call_openai が存在するか確認
has_openai = "_call_openai" in text
print(f"_call_openai 定義存在: {has_openai}")

# _call_anthropic の直後に挿入
call_openai_func = """

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
    return resp
"""

# _call_anthropic 関数の終わり（def _response_text の直前）に挿入
if "def _response_text" in text and "_call_openai" not in text:
    text = text.replace("def _response_text", call_openai_func + "\ndef _response_text")
    st_path.write_text(text, encoding="utf-8")
    print("OK: _call_openai 追加")
elif "_call_openai" in text:
    print("既に存在（定義の場所を確認）")
    for i, l in enumerate(text.splitlines(), 1):
        if "def _call_openai" in l:
            print(f"  Line {i}: {l}")
else:
    print("NG: 挿入ポイント見つからない")

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
print(f"syntax: {r.stdout.strip() or r.stderr.strip()[:120]}")
