"""パイプラインを1件だけテスト実行 - sys.path方式"""

import os
import sys

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline")
os.chdir(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline")

import mail_pipeline as mp

mp.FETCH_LIMIT = 5
mp.PROCESS_LIMIT = 1

# バックアップ（テスト後に戻す）
bak = mp.PROCESSED_IDS_PATH.with_suffix(".json.bak2")
if mp.PROCESSED_IDS_PATH.exists():
    import shutil

    shutil.copy(mp.PROCESSED_IDS_PATH, bak)
    mp.PROCESSED_IDS_PATH.unlink()

mp.main()
print("=== テスト完了 ===")
