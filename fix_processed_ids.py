import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

IMP = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_attachment_importer"
pid_path = IMP + r"\processed_ids.json"

with open(pid_path, encoding="utf-8") as f:
    pids = json.load(f)

# バックアップ
with open(pid_path + ".bak_trim", "w", encoding="utf-8") as f:
    json.dump(pids, f, ensure_ascii=False)

# sessalesは直近3000件のみ保持（古いものは既に再処理されないので削除OK）
# matsuno/okamotoは全件保持（件数少ない）
KEEP_LIMIT = 3000
before = {k: len(v) for k, v in pids.items()}

if len(pids.get("sessales", [])) > KEEP_LIMIT:
    pids["sessales"] = pids["sessales"][-KEEP_LIMIT:]  # 最新3000件を残す

after = {k: len(v) for k, v in pids.items()}

with open(pid_path, "w", encoding="utf-8") as f:
    json.dump(pids, f, ensure_ascii=False)

new_size = os.path.getsize(pid_path)
print("processed_ids 整理完了")
for k in pids:
    print(f"  {k}: {before[k]}件 → {after[k]}件")
print(f"ファイルサイズ: 133683 → {new_size} bytes")

# importer.pyにも自動トリム処理を追加
imp_path = IMP + r"\importer.py"
with open(imp_path, encoding="utf-8") as f:
    imp = f.read()

# save_processed_id関数にトリム処理を追加
old_save = """def save_processed_id(uid: str, account: str = "sessales"):
    ids = load_processed_ids()
    if account not in ids:
        ids[account] = []
    if uid not in ids[account]:
        ids[account].append(uid)
    with open(PROCESSED_IDS_PATH, "w", encoding="utf-8") as f:
        json.dump(ids, f, ensure_ascii=False)"""

new_save = """PROCESSED_IDS_KEEP = 3000  # sessalesは最新3000件のみ保持

def save_processed_id(uid: str, account: str = "sessales"):
    ids = load_processed_ids()
    if account not in ids:
        ids[account] = []
    if uid not in ids[account]:
        ids[account].append(uid)
    # sessalesは件数が多いので古いものをトリム
    if account == "sessales" and len(ids[account]) > PROCESSED_IDS_KEEP:
        ids[account] = ids[account][-PROCESSED_IDS_KEEP:]
    with open(PROCESSED_IDS_PATH, "w", encoding="utf-8") as f:
        json.dump(ids, f, ensure_ascii=False)"""

if old_save in imp:
    imp = imp.replace(old_save, new_save, 1)
    with open(imp_path, "w", encoding="utf-8") as f:
        f.write(imp)
    print("importer.py 自動トリム処理追加OK")
else:
    print("importer.py save_processed_id: 対象行が見つかりません")
