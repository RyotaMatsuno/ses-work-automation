# -*- coding: utf-8 -*-
"""text_parserの単体テスト（区切り線分割のみ、API不要）"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from attachment_importer.parsers.text_parser import split_into_blocks

SAMPLE_1 = """
おつかれさまです！現在5月から案件でお世話になっています。
------------------------------
【名　前】H.S（55歳/男性）
【最寄駅】北小金駅
【稼　働】7月～
【単　金】70万
【スキル】Java、Spring、JavaScript
------------------------------
"""

SAMPLE_2 = """
@All お世話になっております。3名営業しています。
ーーーーーーーーーーーーー
■氏名：OA（33歳・女性）
■最寄り駅：森林公園駅
■希望単価：60万
■スキル概要：Java,C#,React
ーーーーーーーーーーーーー
ーーーーーーーーーーーーー
氏名：R.H（男性／24歳）
最寄駅：学芸大学駅
希望単価：45万～50万円
スキル：Java／PostgreSQL
ーーーーーーーーーーーーー
ーーーーーーーーーーーーー
氏名:U.H／33歳／男性
希望単価：45万円
スキル：C#／C／C++
ーーーーーーーーーーーーー
"""


def test_split_single():
    blocks = split_into_blocks(SAMPLE_1)
    assert len(blocks) == 1, f"Expected 1 block, got {len(blocks)}"
    assert "H.S" in blocks[0]
    print("test_split_single: OK")


def test_split_multiple():
    blocks = split_into_blocks(SAMPLE_2)
    assert len(blocks) == 3, f"Expected 3 blocks, got {len(blocks)}: {blocks}"
    names = ["OA", "R.H", "U.H"]
    for i, name in enumerate(names):
        assert name in blocks[i], f"Expected '{name}' in block {i}"
    print("test_split_multiple: OK")


if __name__ == "__main__":
    test_split_single()
    test_split_multiple()
    print("All tests passed.")
