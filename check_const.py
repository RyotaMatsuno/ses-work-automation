import io
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# 現在の定数ブロックの末尾を確認して、そこに確実に追加
paths = [
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py",
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py",
]

for path in paths:
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    fname = "/".join(path.split("\\")[-2:])

    # 定数ブロックの最後の行（====区切りの前）を探す
    end_marker = "# ======"
    idx_end = src.find(end_marker)
    if idx_end < 0:
        print(f"❌ {fname}: 定数ブロック末尾が見つからない")
        continue

    # そこまでのブロックに PROP_INPUT_SRC があるか確認
    const_block = src[:idx_end]
    if "PROP_INPUT_SRC" in const_block:
        print(f"✅ {fname}: 定数ブロック内にPROP_INPUT_SRC確認済み")
        # 念のため確認
        idx = const_block.rfind("PROP_INPUT_SRC")
        line = const_block[:idx].count("\n") + 1
        print(f"  L{line}: {const_block[idx : idx + 60]}")
    else:
        print(f"❌ {fname}: 定数ブロック外 → 移動が必要")
        # 定数ブロックの最後（====の直前）に挿入
        insert_pos = idx_end
        # 前の行の終わりを探す
        prev_nl = src.rfind("\n", 0, insert_pos)
        new_line = '\nPROP_INPUT_SRC = bytes.fromhex("e585a5e58a9be58583").decode()              # \u5165\u529b\u5143'
        src = src[:prev_nl] + new_line + src[prev_nl:]
        with open(path, "w", encoding="utf-8") as f:
            f.write(src)
        r = subprocess.run(["python", "-m", "py_compile", path], capture_output=True, text=True)
        print(f"  {'✅' if r.returncode == 0 else '❌'} 追加・構文{'OK' if r.returncode == 0 else r.stderr[:80]}")

    print()
