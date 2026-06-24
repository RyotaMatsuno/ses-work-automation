# 【Cursor作業指示】Week3 Task F: freee monthly退役 + FT階段粗利

対象ディレクトリ: ses_work/freee/
作業内容: (1)monthly無効化 (2)FT粗利ロジック修正
完了条件: monthly無効化確認 + FT粗利テスト
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 修正1: freee_invoice_monthly.py 退役（CEO承認済み）

### 手順
1. Task Scheduler で SES_Freee_Invoice_Monthly を Disabled に変更
2. freee_invoice_monthly.py の先頭に以下を追加（安全装置）:
```python
print("このスクリプトは廃止されました。freee_invoice_v2.py を使用してください。")
sys.exit(0)
```
3. README/INFRA_SUMMARYを更新: monthly廃止、v2一本化

### 注意
- ファイルは削除しない（ロールバック用に残す）
- v2（freee_invoice_v2.py）が正常稼働していることを確認してから実施

---

## 修正2: FT階段粗利の実装

### 問題
コード上はFT粗利が一律68%。契約マスター（Google Sheets）には
9件→68%, 11件→75%, 14件→80% の階段が定義されているが未実装。

### 修正方針
1. freee_invoice_v2.py の粗利計算部分に契約マスターの件数参照ロジック追加
2. 契約マスター（Google Sheets ID: 1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI）
   からFT稼働件数を取得 → 階段テーブルで粗利率を決定
3. 階段テーブル:
   - 10件以下: 68%
   - 11-13件: 75%
   - 14件以上: 80%

### テスト追加
- FT 9件 → 68%
- FT 11件 → 75%
- FT 14件 → 80%

---

## 共通ルール
- 既存テスト全パス / 新規コードにtype hint
