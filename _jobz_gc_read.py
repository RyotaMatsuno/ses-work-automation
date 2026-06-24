import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = os.getcwd()

# gate_checker の全ファイル確認
print("■ gate_checker/ ディレクトリ構成")
gc_dir = os.path.join(SES, "gate_checker")
if os.path.isdir(gc_dir):
    for fn in sorted(os.listdir(gc_dir)):
        fp = os.path.join(gc_dir, fn)
        if os.path.isfile(fp):
            sz = os.path.getsize(fp)
            print(f"  {fn} ({sz}b)")
        else:
            print(f"  {fn}/")
else:
    print("  gate_checker/ 未存在")

# gate_check.py 全内容
print("\n■ gate_check.py 全内容")
gc_py = os.path.join(gc_dir, "gate_check.py")
if os.path.exists(gc_py):
    with open(gc_py, encoding="utf-8", errors="replace") as f:
        print(f.read())
else:
    print("  未存在")
