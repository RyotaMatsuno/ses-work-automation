import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# PROP_INPUT_SRC が追加されたか確認、なければ追加
paths = [
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py",
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py",
]
import subprocess

for path in paths:
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    fname = "/".join(path.split("\\")[-2:])

    if "PROP_INPUT_SRC" in src:
        print(f"✅ {fname}: PROP_INPUT_SRC 既存")
        continue

    # PROP_AFFIL_MAIL の後に追加
    OLD = 'PROP_AFFIL_MAIL = bytes.fromhex("e68980e5b19ee383a1e383bce383ab").decode()  # \u6240\u5c5e\u30e1\u30fc\u30eb'
    NEW = OLD + '\nPROP_INPUT_SRC = bytes.fromhex("e585a5e58a9be58583").decode()              # \u5165\u529b\u5143'
    if OLD in src:
        src = src.replace(OLD, NEW, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(src)
        r = subprocess.run(["python", "-m", "py_compile", path], capture_output=True, text=True)
        print(
            f"{'✅' if r.returncode == 0 else '❌'} {fname}: PROP_INPUT_SRC追加・構文{'OK' if r.returncode == 0 else r.stderr}"
        )
    else:
        # 定数ブロック末尾に追加
        ins = src.find("# ====")
        if ins > 0:
            before = src[:ins]
            src = (
                before.rstrip()
                + '\nPROP_INPUT_SRC = bytes.fromhex("e585a5e58a9be58583").decode()  # \u5165\u529b\u5143\n'
                + src[ins:]
            )
            with open(path, "w", encoding="utf-8") as f:
                f.write(src)
            r = subprocess.run(["python", "-m", "py_compile", path], capture_output=True, text=True)
            print(
                f"{'✅' if r.returncode == 0 else '❌'} {fname}: PROP_INPUT_SRC追加・構文{'OK' if r.returncode == 0 else r.stderr}"
            )
