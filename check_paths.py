import pathlib, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
# Desktop配下にses_workがあるか確認
p1 = pathlib.Path(r'C:\Users\ma_py\OneDrive\Desktop\ses_work')
p2 = pathlib.Path(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work')
print(f"Desktop/ses_work exists: {p1.exists()}")
print(f"デスクトップ/ses_work exists: {p2.exists()}")
