# -*- coding: utf-8 -*-
"""
cursor_inject.py
Cursorのエージェント/Composerに自動でテキストを投入するスクリプト。
jobz-commandまたはタスクスケジューラから呼ぶ。

使い方:
  python cursor_inject.py "pending_tasks/ を確認して順番に実行してください"
"""

import argparse
import subprocess
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def find_cursor_window():
    """Cursorのウィンドウハンドルを取得"""
    import pygetwindow as gw

    wins = gw.getWindowsWithTitle("Cursor")
    # "agent - Cursor" や "ses_work - Cursor" など
    agent_wins = [w for w in wins if w.title.strip()]
    if agent_wins:
        return agent_wins[0]
    if wins:
        return wins[0]
    return None


def inject_to_cursor(text: str, wait_sec: float = 1.5) -> bool:
    """CursorのComposerにテキストを投入してEnterを押す"""
    import pyautogui

    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.1

    win = find_cursor_window()
    if not win:
        print("ERROR: Cursorウィンドウが見つかりません")
        return False

    print(f"対象ウィンドウ: {win.title}")

    # ウィンドウをアクティブ化
    try:
        win.activate()
    except Exception:
        pass
    time.sleep(wait_sec)

    # Ctrl+L でComposer/チャットにフォーカス
    pyautogui.hotkey("ctrl", "l")
    time.sleep(0.8)

    # テキスト入力（クリップボード経由で日本語対応）
    subprocess.run(["powershell", "-Command", f"Set-Clipboard -Value '{text}'"], capture_output=True)
    time.sleep(0.3)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.5)

    # Enter送信
    pyautogui.press("enter")
    print(f"投入完了: {text[:50]}")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("text", nargs="?", default="pending_tasks/ を確認して順番に実行してください")
    args = parser.parse_args()
    inject_to_cursor(args.text)


if __name__ == "__main__":
    main()
