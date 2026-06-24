import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
import importlib

import line_query

importlib.reload(line_query)

# GROSS_THRESHOLDS の中身
sys.stdout.buffer.write(f"GROSS_THRESHOLDS: {line_query.GROSS_THRESHOLDS}\n".encode("utf-8"))

# _gross_threshold テスト
for assignee in ["松野", "岡本", "", None, "松野担当", "松"]:
    t = line_query._gross_threshold(assignee)
    sys.stdout.buffer.write(f"  _gross_threshold({assignee!r}) = {t}\n".encode("utf-8"))

# calc_gross_profit テスト
for budget, cost in [(0, 70), (70, 65), (75, 70), (90, 70)]:
    g = line_query.calc_gross_profit(budget, cost)
    sys.stdout.buffer.write(f"  calc_gross_profit({budget}, {cost}) = {g}\n".encode("utf-8"))

# budget=0 の案件は除外すべき -> gross < 0 は全部除外でよいか確認
sys.stdout.buffer.write(b"\nbudget=0 case: gross=-70, threshold=3, -70 < 3 = True -> should CONTINUE (exclude)\n")
sys.stdout.buffer.write(f"  -70 < 3: {-70 < 3}\n".encode("utf-8"))
