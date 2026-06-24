import io
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

paths = [
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py",
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py",
]

for path in paths:
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    fname = "/".join(path.split("\\")[-2:])

    # 現在の PROP_INPUT_SRC の位置を確認
    idx = src.find("PROP_INPUT_SRC")
    if idx < 0:
        print(f"❌ {fname}: PROP_INPUT_SRC なし")
        continue

    # どの行にあるか
    line_num = src[:idx].count("\n") + 1
    context = src[max(0, idx - 50) : idx + 80]
    print(f"{fname}: L{line_num} → {repr(context[:80])}")

    # 正しい位置（VAL_ADJUSTING の直後）に移動
    # まず今の定義を削除
    # パターン1: 末尾に追加された場合
    bad_pattern1 = '\nPROP_INPUT_SRC = bytes.fromhex("e585a5e58a9be58583").decode()  # \u5165\u529b\u5143\n'
    bad_pattern2 = '\nPROP_INPUT_SRC = bytes.fromhex("e585a5e58a9be58583").decode()              # \u5165\u529b\u5143\n'

    # 削除してから正しい位置に挿入
    for bp in [bad_pattern1, bad_pattern2]:
        if bp in src:
            src = src.replace(bp, "\n", 1)
            break

    # VAL_ADJUSTING の後に挿入
    old_adj = 'VAL_ADJUSTING  = bytes.fromhex("e8aabfe695b4e4b8ad").decode()              # \u8abf\u6574\u4e2d'
    new_adj = (
        old_adj + '\nPROP_INPUT_SRC = bytes.fromhex("e585a5e58a9be58583").decode()              # \u5165\u529b\u5143'
    )

    if old_adj in src and "PROP_INPUT_SRC" not in src:
        src = src.replace(old_adj, new_adj, 1)
        print("  → 正しい位置に挿入")
    elif "PROP_INPUT_SRC" in src:
        # まだある = 削除できていない可能性
        idx2 = src.find("PROP_INPUT_SRC")
        line2 = src[:idx2].count("\n") + 1
        print(f"  → まだ L{line2} に残存、手動確認が必要")
        # 定数ブロック（VAL_ADJUSTING付近）に移動
        if old_adj in src:
            src = src.replace(old_adj, new_adj, 1)
            # 重複削除
            if src.count("PROP_INPUT_SRC") > 1:
                # 後ろの方を削除
                first = src.find("PROP_INPUT_SRC")
                second = src.find("PROP_INPUT_SRC", first + 1)
                if second > 0:
                    line_start = src.rfind("\n", 0, second)
                    line_end = src.find("\n", second)
                    src = src[:line_start] + src[line_end:]
                    print("  → 重複削除完了")

    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    r = subprocess.run(["python", "-m", "py_compile", path], capture_output=True, text=True)
    print(f"  {'✅' if r.returncode == 0 else '❌'} 構文{'OK' if r.returncode == 0 else r.stderr[:80]}")
    print()
