"""
assignee.py - 担当者自動割り振りモジュール

受信アドレスから担当者（松野 / 岡本）を決定する。
共通アドレスは岡本2:松野1のラウンドロビン。
"""

import json
from pathlib import Path

MATSUNO_ADDRESS = "r-matsuno@terra-ltd.co.jp"
OKAMOTO_ADDRESS = "r-okamoto@terra-ltd.co.jp"
COUNTER_PATH = Path(__file__).parent / "assignee_counter.json"


def determine_assignee(to_address: str) -> str:
    """受信アドレスから担当者を決定する"""
    addr = (to_address or "").lower()
    if MATSUNO_ADDRESS in addr:
        return "松野"
    if OKAMOTO_ADDRESS in addr:
        return "岡本"
    # 共通アドレス（sessales等）: ラウンドロビン
    return _round_robin_assignee()


def _round_robin_assignee() -> str:
    """岡本2:松野1のラウンドロビン（count % 3 == 2 → 松野）"""
    try:
        if COUNTER_PATH.exists():
            data = json.loads(COUNTER_PATH.read_text(encoding="utf-8"))
            count = data.get("count", 0)
        else:
            count = 0
        assignee = "松野" if count % 3 == 2 else "岡本"
        COUNTER_PATH.write_text(json.dumps({"count": (count + 1) % 3}), encoding="utf-8")
        return assignee
    except Exception as e:
        print(f"[assignee] カウンターエラー: {e}")
        return "松野"


if __name__ == "__main__":
    # 動作確認
    tests = [
        ("r-matsuno@terra-ltd.co.jp", "松野"),
        ("r-okamoto@terra-ltd.co.jp", "岡本"),
        ("sessales@terra-ltd.co.jp", "岡本"),  # count=0 → 岡本
        ("sessales@terra-ltd.co.jp", "岡本"),  # count=1 → 岡本
        ("sessales@terra-ltd.co.jp", "松野"),  # count=2 → 松野
        ("sessales@terra-ltd.co.jp", "岡本"),  # count=0 → 岡本（リセット）
    ]
    # カウンターリセット
    COUNTER_PATH.write_text(json.dumps({"count": 0}), encoding="utf-8")
    print("=== assignee.py 動作確認 ===")
    all_ok = True
    for addr, expected in tests:
        result = determine_assignee(addr)
        status = "OK" if result == expected else "NG"
        if status == "NG":
            all_ok = False
        print(f"  [{status}] {addr} → {result} (期待: {expected})")
    print(f"\n{'全テストOK' if all_ok else 'NGあり・要確認'}")
