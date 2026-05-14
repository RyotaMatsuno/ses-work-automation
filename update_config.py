import shutil
import os
import subprocess
import time

# Claude終了
subprocess.run(["taskkill", "/F", "/IM", "Claude.exe", "/T"], capture_output=True)
time.sleep(3)

# コピー元
src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config_source.json")

# コピー先
dest_dir = os.path.join(os.environ["LOCALAPPDATA"], "Packages", "Claude_pzs8sxrjxfjjc", "LocalCache", "Roaming", "Claude")
dest = os.path.join(dest_dir, "claude_desktop_config.json")

print(f"コピー元: {src}")
print(f"コピー先: {dest}")

if os.path.exists(dest_dir):
    shutil.copy2(src, dest)
    print("コピー成功")
    
    # 確認
    with open(dest, "r", encoding="utf-8") as f:
        content = f.read()
    print("--- コピー後の内容 ---")
    print(content[:200])
else:
    print(f"コピー先ディレクトリが存在しません: {dest_dir}")

# Claude起動
subprocess.Popen(["cmd", "/c", "start", "", "Claude"])
print("Claude起動中...")
