import os

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
path = os.path.join(base, "mail_pipeline", "mail_pipeline.py")
with open(path, encoding="utf-8") as f:
    content = f.read()

# ===== PATCH 1: classify_email の body[:2000] → body[:8000] =====
# Claude APIのmax_tokensは十分あるので8000文字まで拡張
OLD1 = 'text = f"件名: {subject}\\n\\n{body[:2000]}"'
NEW1 = 'text = f"件名: {subject}\\n\\n{body[:8000]}"'
if OLD1 in content:
    content = content.replace(OLD1, NEW1)
    print("PATCH1 (classify body limit): OK")
else:
    # cp932混じりのため行番号で確認
    for i, line in enumerate(content.split("\n")):
        if "body[:2000]" in line:
            print(f"  Found body[:2000] at line {i + 1}: {repr(line)}")
    print("PATCH1: searching by bytes")

# ===== PATCH 2: register_project の note組み立て - bodyも含める =====
# register_project関数にbodyパラメータを追加し、案件詳細にフル本文を格納

OLD2 = 'def register_project(info: dict, subject: str, sender: str, input_source: str = "", affiliation: str = "") -> bool:'
NEW2 = 'def register_project(info: dict, subject: str, sender: str, input_source: str = "", affiliation: str = "", raw_body: str = "") -> bool:'
if OLD2 in content:
    content = content.replace(OLD2, NEW2)
    print("PATCH2 (register_project signature): OK")
else:
    print("PATCH2: NOT FOUND")

# ===== PATCH 3: note組み立てにraw_bodyを追加 =====
OLD3 = "    note = f\"【メールから自動登録】\\n送信元: {sender}\\n件名: {subject}\\n\\n{info.get('note','')}\""
NEW3 = (
    "    note = f\"【メールから自動登録】\\n送信元: {sender}\\n件名: {subject}\\n\\n{raw_body or info.get('note','')}\""
)
if OLD3 in content:
    content = content.replace(OLD3, NEW3)
    print("PATCH3 (note with raw_body): OK")
else:
    print("PATCH3: NOT FOUND - checking")
    for i, line in enumerate(content.split("\n")):
        if "note = f" in line and "sender" in line:
            print(f"  Found at line {i + 1}: {repr(line)}")

# ===== PATCH 4: Notionのrich_textを2000文字複数ブロックに分割する関数を追加 =====
# register_project内の note[:2000] を split_rich_text(note) に変更

# まず split_rich_text ヘルパー関数を追加（register_project の直前）
HELPER_FUNC = '''
def split_rich_text(text: str, chunk_size: int = 1900) -> list:
    """Notionのrich_textは1ブロック2000文字上限のため複数ブロックに分割する"""
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append({"text": {"content": text[i:i+chunk_size]}})
    return chunks or [{"text": {"content": ""}}]

'''

if "def split_rich_text" not in content:
    content = content.replace("def register_project(", HELPER_FUNC + "def register_project(")
    print("PATCH4 (split_rich_text helper): OK")
else:
    print("PATCH4: ALREADY EXISTS")

# ===== PATCH 5: note[:2000] → split_rich_text(note) =====
OLD5 = '"案件詳細": {"rich_text": [{"text": {"content": note[:2000]}}]}'
NEW5 = '"案件詳細": {"rich_text": split_rich_text(note)}'
if OLD5 in content:
    content = content.replace(OLD5, NEW5)
    print("PATCH5 (案件詳細 split): OK")
else:
    print("PATCH5: NOT FOUND - checking")
    for i, line in enumerate(content.split("\n")):
        if "note[:2000]" in line:
            print(f"  Found at line {i + 1}: {repr(line)}")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("WRITE: OK")

import py_compile

try:
    py_compile.compile(path, doraise=True)
    print("SYNTAX: OK")
except py_compile.PyCompileError as e:
    print(f"SYNTAX ERROR: {e}")
