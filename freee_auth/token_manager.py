"""
freee トークン管理モジュール
- access_tokenは6時間で期限切れ → refresh_tokenで自動更新
- このモジュールをimportするだけでトークン管理が完結
"""
import json, time, requests, os

CLIENT_ID     = "731109064351970"
CLIENT_SECRET = "6rbUbEgQ1i58C7O6Ndg8TQDDQcoO6w9EGkCt_HkWADe9klxnGoN1iNd-vlF0vqkqdVOJYi8nfkYNY9M9evkBJQ"
TOKEN_FILE    = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth\freee_token.json"
COMPANY_ID    = 11712776

def load_token():
    with open(TOKEN_FILE, encoding="utf-8") as f:
        return json.load(f)

def save_token(data):
    data["saved_at"] = int(time.time())
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def refresh_access_token():
    token_data = load_token()
    res = requests.post(
        "https://accounts.secure.freee.co.jp/public_api/token",
        data={
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": token_data["refresh_token"],
        }
    )
    if res.status_code == 200:
        new_data = res.json()
        save_token(new_data)
        print("[TOKEN] リフレッシュ成功")
        return new_data["access_token"]
    else:
        raise Exception(f"Token refresh failed: {res.text}")

def get_access_token():
    """有効なaccess_tokenを返す（期限切れなら自動リフレッシュ）"""
    token_data = load_token()
    saved_at = token_data.get("saved_at", 0)
    expires_in = token_data.get("expires_in", 21600)
    elapsed = int(time.time()) - saved_at
    
    if elapsed > (expires_in - 300):  # 5分前にリフレッシュ
        print(f"[TOKEN] 期限切れ({elapsed}秒経過) → リフレッシュ")
        return refresh_access_token()
    
    return token_data["access_token"]

def get_headers():
    return {"Authorization": f"Bearer {get_access_token()}"}

if __name__ == "__main__":
    # テスト実行
    token = get_access_token()
    print(f"[OK] access_token取得: {token[:20]}...")
    
    # APIテスト
    res = requests.get(
        f"https://api.freee.co.jp/api/1/companies",
        headers=get_headers()
    )
    print(f"[OK] API接続: {res.status_code}")
    for c in res.json().get("companies", []):
        print(f"     事業所: {c.get('display_name')} (ID: {c.get('id')})")
