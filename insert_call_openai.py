import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
st_path = base / "matching_v3" / "structurer.py"
text = st_path.read_text(encoding="utf-8", errors="replace")

call_openai = """

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

# _call_anthropic の定義末尾（Line103〜120）の直後に挿入
old_anchor = """def _response_text(response: Any) -> str:"""
if old_anchor in text:
    text = text.replace(old_anchor, call_openai + "\n" + old_anchor)
    st_path.write_text(text, encoding="utf-8")
    print("OK: _call_openai 挿入完了")
else:
    print("NG")

# 確認
import subprocess

r = subprocess.run(
    [
        "python",
        "-c",
        "import sys; sys.path.insert(0,'matching_v3'); sys.path.insert(0,'.'); "
        "import structurer; print([f for f in dir(structurer) if 'openai' in f.lower()])",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=str(base),
)
print(f"  {r.stdout.strip()}")

r2 = subprocess.run(
    [
        "python",
        "-c",
        "import py_compile; py_compile.compile('matching_v3/structurer.py', doraise=True); print('syntax OK')",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=str(base),
)
print(f"  {r2.stdout.strip() or r2.stderr.strip()[:80]}")
