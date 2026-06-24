import io
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

paths = [
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py",
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py",
]

# 既存パターン末尾の正確な文字列
OLD = '        r"^\\u9001\\u4fe1\\u8005:", r"^\\u4ef6\\u540d:",\n    ]'
# 追加するパターン（「下記案件にて」「技術者を探して」等のフィラー）
NEW = (
    '        r"^\\u9001\\u4fe1\\u8005:", r"^\\u4ef6\\u540d:",\n'
    '        r"\\u4e0b\\u8a18\\u6848\\u4ef6",\n'  # 下記案件
    '        r"\\u6280\\u8853\\u8005\\u3092\\u63a2",\n'  # 技術者を探
    '        r"\\u8981\\u54e1\\u3092\\u63a2",\n'  # 要員を探
    '        r"\\u3054\\u7d39\\u4ecb\\u3092\\u304a\\u9858\\u3044",\n'  # ご紹介をお願い
    '        r"\\u304a\\u9858\\u3044\\u3044\\u305f\\u3057\\u307e\\u3059$",\n'  # お願いいたします
    '        r"^\\u203b",\n'  # ※
    "    ]"
)

for path in paths:
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    if OLD in src:
        src = src.replace(OLD, NEW, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(src)
        r = subprocess.run(["python", "-m", "py_compile", path], capture_output=True, text=True)
        fname = "/".join(path.split("\\")[-2:])
        print(f"{'✅' if r.returncode == 0 else '❌'} {fname}: {'OK' if r.returncode == 0 else r.stderr[:100]}")
    else:
        print(f"❌ パターン不一致: {path}")
