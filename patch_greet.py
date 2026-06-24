import io
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

paths = [
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py",
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py",
]

# 追加するグリートパターン（既存パターンの末尾に追加）
OLD_GREET_END = '        r"^\u9001\u4fe1\u8005:", r"^\u4ef6\u540d:",'
NEW_GREET_END = """        r"^\u9001\u4fe1\u8005:", r"^\u4ef6\u540d:",
        r"\u4e0b\u8a18\u6848\u4ef6\u306b\u3066",   # 下記案件にて
        r"\u4e0b\u8a18\u6848\u4ef6\u3092",           # 下記案件を
        r"\u6280\u8853\u8005\u3092\u63a2\u3057\u3066\u304a\u308a\u307e\u3059",  # 技術者を探しております
        r"\u8981\u54e1\u3092\u63a2\u3057\u3066\u304a\u308a\u307e\u3059",        # 要員を探しております
        r"\u3054\u7d39\u4ecb\u3092\u304a\u9858\u3044\u3044\u305f\u3057\u307e\u3059",  # ご紹介をお願いいたします
        r"\u304a\u9858\u3044\u3044\u305f\u3057\u307e\u3059$",  # お願いいたします
        r"^\u203b", r"^\u00d7",   # ※, ×
        r"^\\*\\*\\*", r"^\\-\\-\\-","""

for path in paths:
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    if OLD_GREET_END in src:
        src = src.replace(OLD_GREET_END, NEW_GREET_END, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(src)
        r = subprocess.run(["python", "-m", "py_compile", path], capture_output=True, text=True)
        fname = "/".join(path.split("\\")[-2:])
        print(f"{'✅' if r.returncode == 0 else '❌'} {fname}: {'OK' if r.returncode == 0 else r.stderr}")
    else:
        print(f"⚠️  パターン不一致: {path.split(chr(92))[-1]}")
