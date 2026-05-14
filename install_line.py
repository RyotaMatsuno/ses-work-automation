import urllib.request
import subprocess
import os

url = "https://desktop.line-scdn.net/win/new/LineInst.exe"
dest = os.path.join(os.path.expanduser("~"), "Downloads", "LineInst.exe")

print("LINEをダウンロード中...")
urllib.request.urlretrieve(url, dest)
print(f"ダウンロード完了: {dest}")

print("インストーラーを起動します...")
subprocess.Popen([dest])
print("画面の指示に従ってインストールしてください。")

input("Press Enter to close.")
