with open("mail_pipeline/mail_pipeline.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

with open("check_line498.txt", "w", encoding="utf-8") as out:
    out.write(f"total: {len(lines)}\n")
    for i in range(494, min(502, len(lines))):
        out.write(f"{i + 1}: {repr(lines[i])}\n")
    # 全絵文字チェック
    bad = [(i + 1, hex(ord(ch))) for i, line in enumerate(lines) for ch in line if ord(ch) > 0x9FFF]
    out.write(f"\nbad chars: {len(bad)}\n")
    for ln, h in bad[:30]:
        out.write(f"  line {ln}: {h}\n")
