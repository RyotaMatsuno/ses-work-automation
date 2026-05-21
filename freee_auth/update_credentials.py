import json, os, shutil

NEW_CLIENT_ID = "731109064351970"
NEW_CLIENT_SECRET = "6rbUbEgQ1i58C7O6Ndg8TQDDQcoO6w9EGkCt_HkWADe9klxnGoN1iNd-vlF0vqkqdVOJYi8nfkYNY9M9evkBJQ"
NEW_TOKEN_FILE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth\freee_token.json"

BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee"
targets = ["auth.py", "freee_invoice.py", "freee_invoice_v2.py"]

for fname in targets:
    fpath = os.path.join(BASE, fname)
    if not os.path.exists(fpath):
        print(f"SKIP (not found): {fname}")
        continue
    
    # バックアップ
    shutil.copy(fpath, fpath + ".bak")
    
    content = open(fpath, encoding="utf-8").read()
    original = content
    
    # Client ID/Secret更新
    content = content.replace("730165581365342", NEW_CLIENT_ID)
    content = content.replace("deK5gH1TW7wVL20s1Fgfayqb4eKD-iiPyumvPV782uE5cJlYfN8bGl6cu_3m6mrYbt-A8-YWxH2eyI6JXNsvkg", NEW_CLIENT_SECRET)
    content = content.replace("deK5gH1TW7wVL2Os1Fgfayqb4eK0-iiPyumvPV782uE5cJIYFN8bGl6cu_3m6mrYbt-A8-YWxH2eyI6JXNsvkg", NEW_CLIENT_SECRET)
    
    # token.jsonのパスを新しいfreee_token.jsonに統一
    content = content.replace(
        'os.path.join(os.path.dirname(__file__), "token.json")',
        f'r"{NEW_TOKEN_FILE}"'
    )
    content = content.replace(
        "token.json",
        "freee_token.json"
    )
    
    if content != original:
        open(fpath, "w", encoding="utf-8").write(content)
        print(f"UPDATED: {fname}")
    else:
        print(f"NO CHANGE: {fname}")

print("\n完了")
