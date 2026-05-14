
import os, sys
sys.stdout.reconfigure(encoding='utf-8')

for logfile in ['cleanup_v2_new.log', 'cleanup_v2.log']:
    if os.path.exists(logfile):
        size = os.path.getsize(logfile)
        import datetime
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(logfile))
        print(f"=== {logfile} ({size}bytes, 更新:{mtime}) ===")
        with open(logfile, 'r', encoding='cp932', errors='replace') as f:
            lines = f.readlines()
        print(f"行数: {len(lines)}")
        print("末尾15行:")
        print("".join(lines[-15:]))
        print()
