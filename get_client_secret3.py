import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

GCLOUD = r"C:\Users\ma_py\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
PROJECT = "ses-work-automation"

# アクセストークンを取得してREST APIで直接叩く
r = subprocess.run([GCLOUD, "auth", "print-access-token"], capture_output=True, text=True, encoding="utf-8", shell=True)
token = r.stdout.strip()
print("token取得:", "OK" if token else "NG", flush=True)

if token:
    import requests

    # OAuth2クライアントをREST APIで取得
    CLIENT_ID_FULL = "74735301292-op9eiut55pjdkhb44p25c6hlokcf01ql.apps.googleusercontent.com"

    # clientauthconfig APIを試す
    url = f"https://clientauthconfig.googleapis.com/v1/projects/{PROJECT}/oauthClients/{CLIENT_ID_FULL}"
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
    print("clientauthconfig:", resp.status_code, resp.text[:500], flush=True)

    # iap APIも試す
    url2 = f"https://iap.googleapis.com/v1/projects/{PROJECT}/iap_web/oauth_clients/{CLIENT_ID_FULL}"
    resp2 = requests.get(url2, headers={"Authorization": f"Bearer {token}"})
    print("iap:", resp2.status_code, resp2.text[:500], flush=True)
