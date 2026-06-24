import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.getcwd())  # ses_work（sheets_reader.py）
import sheets_reader as SR

ss = SR._open()
for tab in ["TERRA", "フラップテック", "グレイスライン"]:
    print("================", tab, "================")
    try:
        data = ss.worksheet(tab).get_all_values()
    except Exception as e:
        print("  worksheet error:", repr(e))
        continue
    print("総行数:", len(data))
    for ri, row in enumerate(data[:5]):
        cells = " | ".join(f"[{ci}]{(c[:16] if c else '')}" for ci, c in enumerate(row))
        print(f"  r{ri}:", cells)
    print("  --- データ行サンプル ---")
    for ri in range(min(5, len(data)), min(9, len(data))):
        row = data[ri]
        cells = " | ".join(f"[{ci}]{(c[:16] if c else '')}" for ci, c in enumerate(row))
        print(f"  r{ri}:", cells)
