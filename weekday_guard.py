# -*- coding: utf-8 -*-
"""
weekday_guard.py - 土日祝は何もせず終了するラッパー
使用方法: python weekday_guard.py <実行したいコマンド...>
例: python weekday_guard.py python matching_v3/matching_v3.py
"""

import subprocess
import sys
from datetime import date

try:
    import jpholiday

    def is_holiday(d):
        return jpholiday.is_holiday(d)
except ImportError:

    def is_holiday(d):
        return False


def is_weekday():
    today = date.today()
    if today.weekday() >= 5:  # 土=5, 日=6
        return False
    if is_holiday(today):
        return False
    return True


if __name__ == "__main__":
    if not is_weekday():
        print(f"[weekday_guard] {date.today()} は土日祝のためスキップ", flush=True)
        sys.exit(0)
    cmd = sys.argv[1:]
    if not cmd:
        print("[weekday_guard] 実行コマンドが指定されていません", flush=True)
        sys.exit(1)
    print(f"[weekday_guard] 平日確認OK -> {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd)
    sys.exit(result.returncode)
