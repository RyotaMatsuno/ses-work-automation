import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = os.getcwd()

# pipeline.log 末尾100行
print("■ mail_pipeline/pipeline.log 末尾100行")
log = os.path.join(SES, "mail_pipeline", "pipeline.log")
if os.path.exists(log):
    sz = os.path.getsize(log)
    print(f"  サイズ: {sz:,} bytes ({sz / 1024 / 1024:.1f}MB)")
    with open(log, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    print(f"  総行数: {len(lines)}")
    print("\n--- 末尾100行 ---")
    for l in lines[-100:]:
        print("  " + l.rstrip())
else:
    print("  未存在")

# common/ skill_reader/ の存在確認
print("\n■ 依存モジュール存在確認")
for d in ["common", "skill_reader", "usage_tracker"]:
    dp = os.path.join(SES, d)
    if os.path.isdir(dp):
        files = os.listdir(dp)
        print(f"  ✅ {d}/ ({len(files)}ファイル)")
        for fn in files[:5]:
            print(f"    {fn}")
    else:
        print(f"  ❌ {d}/ 未存在")
