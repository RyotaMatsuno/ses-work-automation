import re

path = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

print(f"現在のバージョン: {'v9' if 'v9' in content[:100] else '?'}")
print(f"ファイルサイズ: {len(content)}文字")

# v9 → v10
content = content.replace('LINE Webhook Server v9', 'LINE Webhook Server v10', 1)

# ダブルチェック関数を追加（notion_queryの直前）
double_check_func = '''
def run_double_check(proposal_text, candidates_info):
    """ダブルチェックAI: 送信前に提案文を検証・自動修正する"""
    system = """SES proposal double-checker. Reply JSON only.
Check for:
1. Forbidden words: 充足, 即戦力, 弊社, 当社
2. Wrong honorifics: 教えてください->ご教授ください, お願いします->よろしくお願いいたします
3. Unmasked company/person names in proposal body
Return: {"ok": true, "issues": [], "corrected": "same as input if ok"}
If issues found, return corrected text with fixes applied."""

    payload = str({"proposal": proposal_text[:1000], "candidates": candidates_info})
    import json as _json
    result = call_claude(system, _json.dumps({"proposal": proposal_text[:1000], "candidates": candidates_info}, ensure_ascii=False), max_tokens=1000)
    try:
        result_obj = _json.loads(re.sub(r'```json|```', '', result).strip())
        if not isinstance(result_obj, dict):
            return True, [], proposal_text
        return result_obj.get("ok", True), result_obj.get("issues", []), result_obj.get("corrected", proposal_text)
    except Exception as e:
        print(f"[run_double_check] parse error: {e}")
        return True, [], proposal_text

'''

if 'run_double_check' not in content:
    content = content.replace('def notion_query(db_id, filter_obj=None):', double_check_func + 'def notion_query(db_id, filter_obj=None):', 1)
    print("run_double_check 追加済み")
else:
    print("run_double_check 既存")

# 送信処理にダブルチェックを差し込む
DC_BLOCK = '''            # ダブルチェック
            cand_info = [{"name": c["name"], "price": c.get("price", 0)} for c, *_ in target]
            dc_ok, dc_issues, draft = run_double_check(draft, cand_info)
            if not dc_ok:
                issues_str = "\\n".join(f"  ・{i}" for i in dc_issues)
                reply_message(reply_token,
                    f"⚠️ ダブルチェックで問題を検出・修正。\\n\\n問題点:\\n{issues_str}\\n\\n修正後の提案文:\\n{draft[:1200]}\\n\\n確認後「送信して {to_addr}」で再送信してください。",
                    sender_token)
                PENDING_PROPOSALS[pending_key]["proposal_draft"] = draft
                return
'''

if 'ダブルチェック' not in content:
    old = '            # 実際にメール送信\n            account = "matsuno" if sender == "matsuno" else "okamoto"'
    new = DC_BLOCK + '            # 実際にメール送信\n            account = "matsuno" if sender == "matsuno" else "okamoto"'
    if old in content:
        content = content.replace(old, new, 1)
        print("ダブルチェックブロック挿入済み")
    else:
        print("WARNING: 挿入箇所が見つかりません")
else:
    print("ダブルチェックブロック 既存")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

# 構文チェック
import py_compile
try:
    py_compile.compile(path, doraise=True)
    print("構文チェック: OK")
except py_compile.PyCompileError as e:
    print(f"構文エラー: {e}")

print(f"最終ファイルサイズ: {len(content)}文字")
print(f"v10: {'v10' in content[:100]}, run_double_check: {'run_double_check' in content}, DC_block: {'ダブルチェック' in content}")
