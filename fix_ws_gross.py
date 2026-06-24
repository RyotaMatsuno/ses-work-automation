# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WS = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
content = open(WS, encoding="utf-8").read()

OLD = """        if eng_price > 0 and proj_price > 0:
            if gross < 0: continue  # 粗利マイナスは除外
            if not skill_skip and gross > 15: continue  # 通常モードのみ上限チェック"""

NEW = """        if eng_price > 0 and proj_price > 0:
            if gross < 0: continue  # 粗利マイナスは除外
            if skill_skip and gross > 10: continue  # #skill_skip: 粗利上限10万（松野指示 2026-06-15）
            if not skill_skip and gross > 15: continue  # 通常モード: 粗利上限15万"""

if OLD in content:
    content = content.replace(OLD, NEW)
    open(WS, "w", encoding="utf-8").write(content)
    print("webhook_server.py: 粗利上限10万 OK")
else:
    print("ERROR: 対象箇所が見つかりません")
