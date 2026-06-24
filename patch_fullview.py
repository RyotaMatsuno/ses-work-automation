import datetime
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")
import os

lw = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"
lq_path = os.path.join(lw, "line_query.py")

bak = lq_path + f".bak_{datetime.date.today().strftime('%m%d')}_fullview"
shutil.copy(lq_path, bak)
print(f"Backup: {bak}")

with open(lq_path, encoding="utf-8") as f:
    content = f.read()

# 1. LINE_LIMIT = 5000 → 100000（実質制限なし）
# 2. TOP_LIMIT = 5 → 9999（全件）
# 3. _limit_reply: 5000文字超えたら切る処理を削除（全件返す）

OLD_LIMITS = """LINE_LIMIT = 5000
TOP_LIMIT = 5"""
NEW_LIMITS = """LINE_LIMIT = 100000  # 全件表示（LINEは5000文字/メッセージだがsplit_line_messageで分割）
TOP_LIMIT = 9999   # 全件表示"""

# _limit_reply を「全件そのまま返す」に変更
OLD_LIMIT_REPLY = """def _limit_reply(lines: list[str], items: list, formatter, header_page: dict) -> str:
    text = "\\n".join(lines)
    if len(text) <= LINE_LIMIT:
        return text
    limited = []
    for line in lines:
        limited.append(line)
        if line.startswith(_num_label(1)):
            break
    for line in lines[len(limited):]:
        if line.startswith(_num_label(TOP_LIMIT + 1)):
            break
        limited.append(line)
    out = "\\n".join(limited)
    suffix = "\\n(\\u4e0a\\u4f4d5\\u4ef6\\u8868\\u793a)"
    if len(out) + len(suffix) > LINE_LIMIT:
        out = out[: LINE_LIMIT - len(suffix)]
    return out + suffix"""

NEW_LIMIT_REPLY = """def _limit_reply(lines: list[str], items: list, formatter, header_page: dict) -> str:
    # 全件表示（split_line_message側でLINE送信時に分割する）
    return "\\n".join(lines)"""

patched = 0
if OLD_LIMITS in content:
    content = content.replace(OLD_LIMITS, NEW_LIMITS)
    patched += 1
    print("PATCHED: LINE_LIMIT / TOP_LIMIT")
else:
    print("NOT FOUND: LINE_LIMIT block")

if OLD_LIMIT_REPLY in content:
    content = content.replace(OLD_LIMIT_REPLY, NEW_LIMIT_REPLY)
    patched += 1
    print("PATCHED: _limit_reply -> 全件返す")
else:
    print("NOT FOUND: _limit_reply - trying unicode search")
    # unicode版で探す
    idx = content.find("def _limit_reply")
    if idx >= 0:
        print(repr(content[idx : idx + 600]))

if patched == 2:
    with open(lq_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"\n{patched}箇所パッチ完了。保存済み。")
else:
    print(f"\n{patched}箇所のみ。要確認。")
