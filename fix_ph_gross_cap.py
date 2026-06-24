# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LQ = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
WS = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"

for filepath, label in [(LQ, "line_query.py"), (WS, "webhook_server.py")]:
    content = open(filepath, encoding="utf-8").read()

    # #skill_skip時の粗利上限を「なし」→「10万」に変更
    OLD = """            if skill_skip:
                # #skill_skip: 単価のみでマッチ（スキルフィルタ除外・粗利上限なし）
                if gross < 0:
                    continue
                if gross < _th:
                    continue"""

    NEW = """            if skill_skip:
                # #skill_skip: スキルフィルタ除外・粗利上限10万（松野指示 2026-06-15）
                if gross < 0:
                    continue
                if gross > 10:
                    continue
                if gross < _th:
                    continue"""

    if OLD in content:
        content = content.replace(OLD, NEW)
        open(filepath, "w", encoding="utf-8").write(content)
        print(f"{label}: 粗利上限10万 OK")
    else:
        # webhook_server.py側は別の書き方
        OLD2 = """        if skill_skip:
                # #skill_skip: 単価のみでマッチ（スキルフィルタ除外・粗利上限なし）
                if gross < 0:
                    continue
                if gross < _th:
                    continue"""
        NEW2 = """        if skill_skip:
                # #skill_skip: スキルフィルタ除外・粗利上限10万（松野指示 2026-06-15）
                if gross < 0:
                    continue
                if gross > 10:
                    continue
                if gross < _th:
                    continue"""
        if OLD2 in content:
            content = content.replace(OLD2, NEW2)
            open(filepath, "w", encoding="utf-8").write(content)
            print(f"{label}: 粗利上限10万 OK")
        else:
            print(f"{label}: 対象箇所見つからず → 手動確認")
