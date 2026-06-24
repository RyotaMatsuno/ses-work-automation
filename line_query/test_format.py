import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
import importlib

import line_query

importlib.reload(line_query)
from line_query import format_project_result

# ダミーデータでformat_project_resultのエンジニア名表示を確認
# H.Sのような実データを模したダミー
eng = {
    "properties": {
        "\u30a4\u30cb\u30b7\u30e3\u30eb": {"type": "rich_text", "rich_text": []},
        "\u540d\u524d": {"type": "title", "title": [{"plain_text": "H.S"}]},
        "\u6700\u5bc4\u308a\u99c5": {"type": "rich_text", "rich_text": []},
    }
}

result = format_project_result(eng, [])
sys.stdout.buffer.write(result.encode("utf-8"))
sys.stdout.buffer.write(b"\n")
