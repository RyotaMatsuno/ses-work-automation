import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from datetime import datetime

instruction = """【Cursor作業指示】line_query オンデマンドマッチング バグ修正
対象ファイル: ses_work/line_query/line_query.py
参照ファイル: ses_work/line_query/line_query.py
完了条件:
  1. engineer_query() の粗利フィルタが正しく動作する
  2. handle_line_query() がマッチなし時に適切な文字列を返す
  3. python -c "from line_query.line_query import handle_line_query; print(handle_line_query('PH 京成小岩'))" が None 以外を返す

━━━ 修正内容（3点） ━━━

【修正①】line_query/line_query.py の engineer_query() 内

変更前:
            if gross > 15:
                continue  # 粗利上限15万超は単価荵夜屬過大...（文字化け）
            if gross < 0:
                continue  # 粗利マイナス...

変更後:
            if gross < 5:
                continue  # 粗利5万未満は提案不可（判断マニュアルv3 最低粗利5万）
            if gross < 0:
                continue  # 念のため（gross<5で既にカバー）

【修正②】同ファイル engineer_query() 内

変更前:
            if budget > 150:
                continue  # 異常単価除外

変更後:
            # budget > 150 の除外を削除（条件不要）

【修正③】同ファイル handle_line_query() 内

変更前:
        no_match_phrases = (
            "一致する人員が見つかりません",
            "一致する案件が見つかりません",
        )
        if result and any(p in result for p in no_match_phrases):
            return None

変更後:
        # マッチなし時もそのままLINEに返す（Noneにしない）
        # 呼び出し元で処理を続けるとバグる

━━━ 注意 ━━━
- ファイルは cp932 エンコーディングの可能性あり。読み込み時は encoding='cp932' または 'utf-8' で試行する
- 変更は最小限（3箇所のみ）
- 変更後に構文チェック: python -m py_compile line_query/line_query.py

━━━ ゲートチェック ━━━
python gate_checker/gate_check.py --phase implementation --file line_query/line_query.py
"""

os.makedirs("pending_tasks", exist_ok=True)
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
path = f"pending_tasks/{ts}_line_query_bug_fix.md"
with open(path, "w", encoding="utf-8") as f:
    f.write(instruction)
print(f"saved: {path}")
