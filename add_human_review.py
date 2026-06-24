# -*- coding: utf-8 -*-
"""build_queue_progress に松野確認事項セクションを追加する"""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BRIDGE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_bridge.py"

content = open(BRIDGE, encoding="utf-8").read()

# 1. 定数追加（_DEFAULT_QUEUE_DB_ID の直後）
OLD_CONST = '_DEFAULT_QUEUE_DB_ID = "37a450ff-37c0-819a-981b-c2e06ed282bb"'
NEW_CONST = '''_DEFAULT_QUEUE_DB_ID = "37a450ff-37c0-819a-981b-c2e06ed282bb"
_HUMAN_REVIEW_FILE = Path(__file__).resolve().parent.parent / "local_server" / "human_review_items.json"'''

if "_HUMAN_REVIEW_FILE" not in content:
    content = content.replace(OLD_CONST, NEW_CONST)
    print("定数追加OK")
else:
    print("定数は既存")

# 2. 確認事項の読み書き関数を追加（push_or_log の直前）
NEW_FUNCS = '''
def get_human_review_items() -> list[str]:
    """松野への確認・報告事項を読み込む。"""
    try:
        if _HUMAN_REVIEW_FILE.exists():
            data = json.loads(_HUMAN_REVIEW_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
    except Exception:
        pass
    return []


def add_human_review_item(item: str) -> None:
    """確認・報告事項を追加する（ジョブズからのみ呼ぶ）。"""
    items = get_human_review_items()
    now = datetime.now(JST).strftime("%m/%d %H:%M")
    items.append(f"[{now}] {item}")
    # 最大10件まで保持
    items = items[-10:]
    _HUMAN_REVIEW_FILE.parent.mkdir(parents=True, exist_ok=True)
    _HUMAN_REVIEW_FILE.write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def clear_human_review_items() -> None:
    """確認事項をクリアする（松野が確認済みのとき）。"""
    try:
        _HUMAN_REVIEW_FILE.write_text("[]", encoding="utf-8")
    except Exception:
        pass

'''

if "get_human_review_items" not in content:
    # push_or_log の直前に追加
    content = content.replace("\ndef push_or_log(", NEW_FUNCS + "\ndef push_or_log(")
    print("関数追加OK")
else:
    print("関数は既存")

# 3. build_queue_progress の末尾に確認事項セクションを追加
OLD_BQP_END = '''    return "\n".join(lines) if len(lines) > 1 else "AI作業キューは空です。"'''
NEW_BQP_END = '''    # 松野への確認・報告事項
    review_items = get_human_review_items()
    if review_items:
        lines.append("")
        lines.append("📋【松野確認・報告事項】")
        for item in review_items:
            lines.append(f"  {item}")
        lines.append("→ 確認したら「確認済み」と送ってください")

    return "\\n".join(lines) if len(lines) > 1 else "AI作業キューは空です。"'''

if "松野確認・報告事項" not in content:
    content = content.replace(OLD_BQP_END, NEW_BQP_END)
    print("build_queue_progress 修正OK")
else:
    print("build_queue_progress は既存")

# 4. handle_router_message に「確認済み」コマンドを追加
OLD_CMD = '    if stripped == "案件進捗":'
NEW_CMD = """    if stripped == "確認済み":
        clear_human_review_items()
        return {"handled": True, "reply": "確認事項をクリアしました✅"}

    if stripped == "案件進捗":"""

if "確認済み" not in content:
    content = content.replace(OLD_CMD, NEW_CMD)
    print("確認済みコマンド追加OK")
else:
    print("確認済みコマンドは既存")

with open(BRIDGE, "w", encoding="utf-8") as f:
    f.write(content)
print("line_bridge.py 書き込み完了")

# 動作確認
import subprocess

r = subprocess.run(
    [
        sys.executable,
        "-c",
        "import sys; sys.path.insert(0, r'C:\\Users\\ma_py\\OneDrive\\デスクトップ\\ses_work'); "
        "from line_webhook.line_bridge import get_human_review_items, add_human_review_item, clear_human_review_items, build_queue_progress; "
        "add_human_review_item('テスト: PHさんのマッチング結果を確認してください'); "
        "items = get_human_review_items(); "
        "print('items:', items); "
        "clear_human_review_items(); "
        "print('clear OK')",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
    timeout=15,
)
print(r.stdout.strip())
if r.stderr:
    print("ERR:", r.stderr[:300])
