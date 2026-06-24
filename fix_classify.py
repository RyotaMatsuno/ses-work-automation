import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import subprocess

# ===========================================================================
# 修正6: classify_query で initial を _normalize_initial に通す
# 修正7: handle_line_query の50文字ガードを正確に直す
# ===========================================================================

paths = [
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py",
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py",
]

for path in paths:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    fname = "/".join(path.split("\\")[-2:])

    # --- 修正6: classify_queryでinitialを正規化 ---
    OLD_CLASSIFY = '        return ("engineer", {"initial": match.group(1).upper(), "station": match.group(2).strip()})'
    NEW_CLASSIFY = '        _raw_ini = re.sub(r\'[.\\\\s\\\\u3000]\', \'\', match.group(1)).upper()\n        return ("engineer", {"initial": _raw_ini, "station": match.group(2).strip()})'

    if OLD_CLASSIFY in content:
        content = content.replace(OLD_CLASSIFY, NEW_CLASSIFY, 1)
        print(f"✅ {fname}: 修正6(classify_query正規化) OK")
    else:
        print(f"❌ {fname}: 修正6パターン不一致")
        idx = content.find('return ("engineer"')
        if idx >= 0:
            print(f"  実際: {repr(content[idx : idx + 120])}")

    # --- 修正7: handle_line_queryの50文字ガードを確認・修正 ---
    # 50文字超をスルーするのは正しいが、project_queryが短いテキストで誤動作している
    # 「Web系のJAVA案件ありましたらお願いします！長期案件リモー」= 34文字 → 50文字以下でproject_queryに入る
    # これが「一致する案件が見つかりません」になる原因

    # 50文字ガードを100文字に変更（スキルシート本文は必ず100文字以上）
    OLD_GUARD = "    # 50文字超はサマリー文章のためスルー（クエリ専用）\n    if text and len(text.strip()) > 50:\n        return None"
    NEW_GUARD = "    # 100文字超はスキルシート本文・長文メッセージのためスルー（クエリ専用）\n    if text and len(text.strip()) > 100:\n        return None"

    if OLD_GUARD in content:
        content = content.replace(OLD_GUARD, NEW_GUARD, 1)
        print(f"✅ {fname}: 修正7(ガード100文字化) OK")
    else:
        # 別パターンを試す
        OLD_GUARD2 = "    # 50文字超はサマリー文章のためスルー（クエリ専用関数）\n    if text and len(text.strip()) > 50:\n        return None"
        NEW_GUARD2 = "    # 100文字超はスキルシート本文・長文メッセージのためスルー（クエリ専用）\n    if text and len(text.strip()) > 100:\n        return None"
        if OLD_GUARD2 in content:
            content = content.replace(OLD_GUARD2, NEW_GUARD2, 1)
            print(f"✅ {fname}: 修正7(ガード100文字化) OK")
        else:
            print(f"❌ {fname}: 修正7パターン不一致")
            idx = content.find("50文字")
            if idx >= 0:
                print(f"  実際: {repr(content[max(0, idx - 50) : idx + 150])}")

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    # 構文チェック
    r = subprocess.run(["python", "-m", "py_compile", path], capture_output=True, text=True)
    if r.returncode == 0:
        print(f"✅ {fname}: 構文OK")
    else:
        print(f"❌ {fname}: 構文エラー {r.stderr}")
    print()

# webhook_server.pyのhandle_line_query呼び出し箇所も同じコードを参照しているかチェック
webhook_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(webhook_path, "r", encoding="utf-8") as f:
    ws = f.read()

# どちらのline_queryを使っているか確認
if "from line_query import handle_line_query" in ws:
    print("webhook_server.py → line_query（同ディレクトリ）を使用")
elif "from line_webhook.line_query" in ws:
    print("webhook_server.py → line_webhook.line_queryを使用")
else:
    # インライン確認
    idx = ws.find("line_query")
    print(f"line_query参照箇所: {repr(ws[max(0, idx - 30) : idx + 100])}")
