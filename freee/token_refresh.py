# -*- coding: utf-8 -*-
"""
freee OAuthトークン自動更新モジュール
token_manager.pyと同じfreee_token.jsonを参照するよう修正版
"""

import json
import time
import requests
from pathlib import Path

# freee_invoice_v2.pyが参照するtoken_managerと同じファイルを使う
TOKEN_PATH = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth\freee_token.json")
CLIENT_ID = "731109064351970"
CLIENT_SECRET = "6rbUbEgQ1i58C7O6Ndg8TQDDQcoO6w9EGkCt_HkWADe9klxnGoN1iNd-vlF0vqkqdVOJYi8nfkYNY9M9evkBJQ"
TOKEN_URL = "https://accounts.secure.freee.co.jp/public_api/token"

def load_token() -> dict:
    with open(TOKEN_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_token(token: dict):
    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        json.dump(token, f, ensure_ascii=False, indent=2)
    print(f"[token_refresh] トークン保存完了")

def is_token_expired(token: dict, buffer_sec: int = 300) -> bool:
    created_at = token.get("created_at", 0)
    expires_in = token.get("expires_in", 86400)
    return time.time() > (created_at + expires_in - buffer_sec)

def refresh_access_token(token: dict) -> dict:
    resp = requests.post(TOKEN_URL, data={
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": "http://localhost:8080/callback",
        "refresh_token": token["refresh_token"],
    })
    if resp.status_code not in (200, 201):
        raise Exception(f"トークン更新失敗: {resp.status_code} {resp.text}")
    new_token = resp.json()
    new_token["created_at"] = int(time.time())
    save_token(new_token)
    print(f"[token_refresh] アクセストークン自動更新完了")
    return new_token

def get_valid_token() -> dict:
    token = load_token()
    if is_token_expired(token):
        print(f"[token_refresh] トークン失効 → refresh_tokenで自動更新")
        token = refresh_access_token(token)
    else:
        remaining = (token["created_at"] + token["expires_in"]) - time.time()
        print(f"[token_refresh] トークン有効 (残り {int(remaining/60)} 分)")
    return token

if __name__ == "__main__":
    t = get_valid_token()
    print(f"access_token: {t['access_token'][:20]}...")
