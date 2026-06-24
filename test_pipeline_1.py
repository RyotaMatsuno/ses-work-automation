"""パイプラインを1件だけテスト実行"""

import sys

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline")

# 上限を一時的に1件にしてインポート前に環境変数設定
import os

os.chdir(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")


# mail_pipeline モジュールを読み込んで定数を上書き
import mail_pipeline.mail_pipeline as mp

mp.FETCH_LIMIT = 5
mp.PROCESS_LIMIT = 1

# processed_idsをクリア（テスト用）
if mp.PROCESSED_IDS_PATH.exists():
    mp.PROCESSED_IDS_PATH.rename(mp.PROCESSED_IDS_PATH.with_suffix(".json.bak"))

mp.main()
