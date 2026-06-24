import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ses_work = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
log_path = ses_work / "mail_pipeline" / "pipeline.log"

with open(log_path, encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

# "新規処理対象" の行を全部集める
new_proc = [l.strip() for l in lines if "新規処理対象" in l]
print(f"'新規処理対象' 行の総数: {len(new_proc)}")
print("\n--- 直近10件 ---")
for l in new_proc[-10:]:
    print(l)

# "取得完了" の行も
total_fetch = [l.strip() for l in lines if "取得完了" in l]
print(f"\n'取得完了' 行の総数: {len(total_fetch)}")
print("\n--- 直近5件 ---")
for l in total_fetch[-5:]:
    print(l)

# 処理済みDB存在確認
db_candidates = [
    ses_work / "mail_pipeline" / "processed_ids.db",
    ses_work / "mail_pipeline" / "processed_ids.json",
    ses_work / "mail_pipeline" / "processed.db",
    ses_work / "mail_pipeline" / "processed.json",
    ses_work / "processed_ids.db",
]
print("\n--- 処理済みDB確認 ---")
for p in db_candidates:
    status = "EXISTS" if p.exists() else "なし"
    print(f"{p}: {status}")

# mail_pipeline ディレクトリ内ファイル一覧
mp_dir = ses_work / "mail_pipeline"
print(f"\n--- {mp_dir} 内ファイル ---")
if mp_dir.exists():
    for f in sorted(mp_dir.iterdir()):
        size = f.stat().st_size if f.is_file() else 0
        print(f"  {f.name}  ({size:,} bytes)")
