import io
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

paths = [
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py",
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py",
]

OLD = 'PROP_OPTSK     = bytes.fromhex("e5b09ae58fabe382b9e382ade383ab").decode()   # 尚可スキル'
NEW = 'PROP_OPTSK     = bytes.fromhex("e5b09ae58fafe382b9e382ade383ab").decode()   # 尚可スキル'

# 修正前後を確認
print(f"修正前: {bytes.fromhex('e5b09ae58fabe382b9e382ade383ab').decode()}")
print(f"修正後: {bytes.fromhex('e5b09ae58fafe382b9e382ade383ab').decode()}")
print()

for path in paths:
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    if OLD in src:
        src = src.replace(OLD, NEW, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(src)
        r = subprocess.run(["python", "-m", "py_compile", path], capture_output=True, text=True)
        fname = "/".join(path.split("\\")[-2:])
        ok = r.returncode == 0
        print(f"{'✅' if ok else '❌'} {fname}: PROP_OPTSK修正{'・構文OK' if ok else '・構文エラー: ' + r.stderr}")
    else:
        print(f"⚠️  {path}: パターン不一致")
        # 現在の行を表示
        for line in src.splitlines():
            if "PROP_OPTSK" in line:
                print(f"   現在: {line}")
