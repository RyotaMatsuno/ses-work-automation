#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""MODEL_ROUTING.md の 2026-06-01〜04 セクションを真因確定情報に更新"""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

path = "C:/Users/ma_py/OneDrive/デスクトップ/ses_work/MODEL_ROUTING.md"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = """### 2026-06-01〜04: Anthropic 直接課金 累計約$220 スパイク
- **原因**: mail_pipeline FETCH_LIMIT 上限なし + 重複処理 ($50.88/日 インシデント含む)
- **対応済み**: CostGuard 実装 + Cursor完全移行(6/09) + ChatGPT Plus解約(6/12)
- **現状**: 6/05以降 Anthropic 直接課金は$1-2/日でほぼゼロ
- **教訓**: API直叩きスクリプトは必ず ledger.py 経由 (装置1〜4で再発防止強化中)"""

new = """### 2026-06-01〜04: Anthropic 直接課金 累計約$220 スパイク (真因確定 2026-06-16)
- **真因(松野証言)**:
  - 要因A: 2026-06-02 の mail_pipeline インシデント ($50.88/日, FETCH_LIMIT上限なし+重複処理)
  - 要因B: Claude.ai (Claude Pro 月額)のチャットトークン枠不足のためのトークン追加購入 (松野が意図的に実施)
  - → 要因Bは「再発リスク」ではなく合理的な追加支出
- **対応済み**: CostGuard 実装 + Cursor完全移行(6/09) + ChatGPT Plus解約(6/12)
- **現状**: 6/05以降 Anthropic 直接課金は$1-2/日でほぼゼロ
- **教訓1**: API直叩きスクリプトは必ず ledger.py 経由 (装置1〜4で再発防止強化中)
- **教訓2**: ジョブズが実測データだけで因果を確定するのはリスク。「ジョブズの解釈」を明示して松野の修正機会を作る運用に変更"""

if old in content:
    content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("OK MODEL_ROUTING.md 更新完了")
    print(f"   新サイズ: {len(content)} chars")
else:
    print("NG old not found")
    # 既存内容のうち該当部分を表示
    import re

    m = re.search(r"### 2026-06-01.*?(?=### |\Z)", content, flags=re.S)
    if m:
        print("Current section:")
        print(m.group(0)[:600])
