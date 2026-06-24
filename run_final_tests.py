import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
LW = os.path.join(BASE, "line_webhook")

# 1. 構文チェック
print("=== FINAL TEST 1: line_query.py 構文チェック ===", flush=True)
r = subprocess.run(
    ["python", "-m", "py_compile", "line_query.py"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=LW,
)
print("結果:", "OK ✅" if r.returncode == 0 else f"NG ❌\n{r.stderr[:300]}", flush=True)

# 2. classify_queryバグ修正確認
print("\n=== FINAL TEST 2: classify_query 修正確認 ===", flush=True)

# line_query.pyからclassify_query関数を抽出して実行
with open(os.path.join(LW, "line_query.py"), encoding="utf-8") as f:
    src = f.read()

# 関数部分を抜き出してexec
import_block = "import re\n"
func_match = re.search(r"(def classify_query\(text.*?)(?=\ndef )", src, re.DOTALL)
if func_match:
    func_src = import_block + func_match.group(1)
    local_ns = {}
    exec(func_src, local_ns)
    classify_query = local_ns["classify_query"]

    test_cases = [
        ("HS 北小金", "engineer"),
        ("H.S 北小金", "engineer"),
        ("TK 渋谷", "engineer"),
        ("Oracle DBマイグレーション", "project"),
        ("Java Spring案件 渋谷", "project"),
        ("某金融系Java開発", "project"),
        ("詳細 ①", "project"),
    ]
    all_pass = True
    for text, expected in test_cases:
        qtype, params = classify_query(text)
        ok = qtype == expected
        if not ok:
            all_pass = False
        mark = "✅" if ok else "❌"
        print(f'  {mark} "{text}" → {qtype} (期待: {expected})', flush=True)
    print(f"\n  全テスト: {'PASS ✅' if all_pass else 'FAIL ❌'}", flush=True)
else:
    print("  classify_query関数が見つかりません", flush=True)

# 3. _LAST_ENG_RESULTS/_LAST_PROJ_RESULTSの定義確認
print("\n=== FINAL TEST 3: キャッシュ変数定義確認 ===", flush=True)
for var in ["_LAST_ENG_RESULTS", "_LAST_PROJ_RESULTS", "_LAST_QUERY_TYPE"]:
    if var in src:
        print(f"  {var}: ✅ 定義あり", flush=True)
    else:
        print(f"  {var}: ❌ 未定義", flush=True)

# 4. format_engineer_detail関数の存在確認
print("\n=== FINAL TEST 4: 新規関数存在確認 ===", flush=True)
for fn in ["format_engineer_detail", "format_project_detail", "_LAST_ENG_RESULTS"]:
    if f"def {fn}" in src or f"{fn}" in src:
        print(f"  {fn}: ✅", flush=True)
    else:
        print(f"  {fn}: ❌ 未定義", flush=True)

# 5. DriveリンクURLの参照確認
print("\n=== FINAL TEST 5: DriveリンクURL参照確認 ===", flush=True)
drive_refs = [l for l in src.splitlines() if "Drive" in l or "drive_url" in l.lower() or "DriveリンクURL" in l]
for ref in drive_refs[:5]:
    print(f"  {ref.strip()}", flush=True)

# 6. 人員情報原文の参照確認
print("\n=== FINAL TEST 6: 人員情報原文参照確認 ===", flush=True)
raw_refs = [l for l in src.splitlines() if "人員情報原文" in l or "raw_body" in l.lower()]
for ref in raw_refs[:5]:
    print(f"  {ref.strip()}", flush=True)
