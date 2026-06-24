import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

# SPEC_project_detail.mdに追記（classify_queryバグ修正も含める）
BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
path = os.path.join(BASE, "line_webhook", "SPEC_project_detail.md")

addition = """

---

## 追加修正: classify_queryのバグ修正

### 問題
「Oracle DBマイグレーション」のような英語始まりの案件名が
engineer（イニシャル判定）に誤分類される。

現在の正規表現: ^([A-Za-z.]{1,8})[\\s\\u3000/]+(.+)$
→ "Oracle" は1〜8文字の英字なので誤マッチする

### 修正方法
イニシャル判定の条件を厳密化する:
- イニシャル部分は最大4文字（"HS", "H.S", "TK", "KY"等）
- 5文字以上の英字は案件名として扱う
- 具体的には正規表現を ^([A-Za-z.]{1,4})[\\s\\u3000/]+(.+)$ に変更

または判定ロジックを変更:
- イニシャル候補の文字数が5文字以上の場合はproject判定に倒す

### テストケース（修正後に全パスすること）
- "HS 北小金" → engineer {initial: "HS", station: "北小金"} ✅
- "H.S 北小金" → engineer {initial: "HS", station: "北小金"} ✅
- "TK 渋谷" → engineer {initial: "TK", station: "渋谷"} ✅
- "Oracle DBマイグレーション" → project {name: "Oracle DBマイグレーション"} ← 修正
- "Java Spring案件 渋谷" → project {name: "Java Spring案件 渋谷"} ← 修正
- "某金融系Java開発" → project ✅
"""

with open(path, "a", encoding="utf-8") as f:
    f.write(addition)

print("SPEC更新完了", flush=True)
