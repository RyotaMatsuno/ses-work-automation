import sys

fpath = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(fpath, "rb") as f:
    raw = f.read()
text = raw.decode("utf-8")

# engineer_query の matched_projects.append 直前にデバッグprint追加
old = '            matched_projects.append({"page": project, "gross_profit": gross})'
new = (
    '            print(f"[match] {_text_prop(project, chr(0x6848)+chr(0x4EF6)+chr(0x540D))} status={_select_prop(project, chr(0x30B9)+chr(0x30C6)+chr(0x30FC)+chr(0x30BF)+chr(0x30B9))} budget={budget} gross={gross:.1f} req_sk={required}", flush=True)\n'
    '            matched_projects.append({"page": project, "gross_profit": gross})'
)

# ステータスフィルタ行にもデバッグ追加
old2 = '            if _select_prop(project, "ステータス") != "募集中":'
new2 = (
    '            _st = _select_prop(project, "ステータス")\n'
    '            if _st != "募集中":\n'
    '                print(f"[skip-status] {_st!r}", flush=True)'
)

new_text = text
if old in new_text:
    new_text = new_text.replace(old, new)
    sys.stdout.buffer.write(b"Added match debug\n")
else:
    sys.stdout.buffer.write(b"match target not found\n")

if old2 in new_text:
    new_text = new_text.replace(old2, new2)
    sys.stdout.buffer.write(b"Added status debug\n")
else:
    sys.stdout.buffer.write(b"status target not found\n")

with open(fpath, "w", encoding="utf-8") as f:
    f.write(new_text)

sys.stdout.buffer.write(b"Written\n")
