spec_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\SPEC.md"
with open(spec_path, encoding="utf-8") as f:
    content = f.read()

# 関連セクションを抜き出す（スキルマッチング関連）
lines = content.splitlines()
in_section = False
out_lines = []
for i, line in enumerate(lines):
    if (
        "skill" in line.lower()
        or "スキル" in line
        or "alias" in line.lower()
        or "正規化" in line
        or "マッチング" in line
    ):
        # 前後5行を出力
        start = max(0, i - 2)
        end = min(len(lines), i + 8)
        for j in range(start, end):
            out_lines.append(f"{j + 1:4d}: {lines[j]}")
        out_lines.append("---")

print("\n".join(out_lines[:200]))
