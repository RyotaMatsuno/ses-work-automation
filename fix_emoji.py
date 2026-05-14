with open('mail_pipeline/mail_pipeline.py', 'r', encoding='utf-8') as f:
    c = f.read()

# 全特殊絵文字を置換
emoji_map = {
    '\u2705': '[OK]',   # ✅
    '\u274c': '[NG]',   # ❌
    '\u26a0': '[!!]',   # ⚠
    '\ufe0f': '',       # variation selector
    '\U0001f4e7': '[MAIL]',  # 📧
    '\u2b50': '[*]',    # ⭐
    '\u2764': '[heart]', # ❤
}
for k, v in emoji_map.items():
    c = c.replace(k, v)

with open('mail_pipeline/mail_pipeline.py', 'w', encoding='utf-8') as f:
    f.write(c)

# 再確認
remaining = [hex(ord(ch)) for ch in c if ord(ch) > 0x9fff]
with open('check_line498.txt', 'w', encoding='utf-8') as out:
    out.write(f"残存特殊文字数: {len(remaining)}\n")
    if remaining:
        out.write(str(set(remaining)))
