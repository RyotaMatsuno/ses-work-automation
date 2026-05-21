import requests
import json

CLIENT_ID = "731109064351970"
CLIENT_SECRET = "6rbUbEgQ1i58C7O6Ndg8TQDDQcoO6w9EGkCt_HkWADe9klxnGoN1iNd-vlF0vqkqdVOJYi8nfkYNY9M9evkBJQ"
CODE = "g6b9Lv1EeFK6J4NuahdMag7OAo_fwygFY3YOaFQPEpA"
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"
TOKEN_FILE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth\freee_token.json"

res = requests.post(
    "https://accounts.secure.freee.co.jp/public_api/token",
    data={
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": CODE,
        "redirect_uri": REDIRECT_URI,
    },
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)

print(f"status: {res.status_code}")
if res.status_code == 200:
    token_data = res.json()
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(token_data, f, indent=2, ensure_ascii=False)
    print(f"SUCCESS: トークン保存完了")
    print(f"access_token: {token_data.get('access_token', '')[:20]}...")
    print(f"expires_in: {token_data.get('expires_in')}秒")
    print(f"refresh_token: {token_data.get('refresh_token', '')[:20]}...")
else:
    print(f"FAILED: {res.text}")
