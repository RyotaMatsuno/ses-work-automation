# Phase3: Ledger接続 - Codex作業ルール
## 編集対象
1. `matching_v3/structurer.py` … record_cost → ledger.record に切替
2. `matching_v3/cost_guard.py` … can_call → ledger.can_spend のラッパーに変更
3. `outlook/outlook_to_notion.py` … モデルをHaikuに変更、ledger組み込み
4. `mail_attachment_importer/ai_extractor.py` … ledger組み込み

## 禁止事項
- matching_v3/matching_v3.py / matcher.py / notifier.py には触れない
- 他ファイルの既存ロジックを変更しない（ledger接続箇所のみ追加）
- common/ledger.py は変更しない

## Import規則
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from common.ledger import can_spend, record as ledger_record
```
