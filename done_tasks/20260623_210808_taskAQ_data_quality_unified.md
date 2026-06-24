# 【Cursor作業指示】Task AQ統合: データ品質一括改善（抽出・正規化・否定条件・ノイズ除去）

対象: ses_work/matching_v3/ + ses_work/common/
参照: CLAUDE.md / structurer.py / matcher.py / skill_aliases.json
完了条件: 全テスト合格 + 各機能の単体テスト追加

---

## ■1. メール本文ノイズ除去（旧Task AV）
新規: common/email_cleaner.py
```python
def clean_email_body(body: str) -> str:
    body = remove_signature(body)      # 「--」以降、Tel:/携帯:/HP:ブロック
    body = remove_disclaimer(body)     # 免責事項「本メールは〜」
    body = remove_quoted_reply(body)   # 「> 」引用、「On ... wrote:」
    body = remove_decoration(body)     # ★☆■□━━━等の装飾のみの行
    body = normalize_whitespace(body)  # 連続空行→1行
    return body.strip()
```
- structurer.py の structure() 冒頭で適用
- mail_pipeline.py の分類前にも適用（分類精度も向上）

## ■2. 必須項目欠落検知+再抽出（旧Task AQ）
structurer.py の structure() 後処理に追加:
- 必須項目: required_skills, rate(min or max), location, 案件名
- 充足率 = 充足数 / 4
- 充足率 < 0.6 → 再抽出1回（簡略プロンプト、max_tokens=2000、CostGuard経由）
- 再抽出でも < 0.6 → quality_flag='NEEDS_REVIEW'
- daily_statsに extraction_retry_count 追加

## ■3. 数値・条件の正規化（旧Task AR）
新規: common/normalizers.py
```python
def normalize_rate(value) -> tuple[float|None, float|None]:
    # 「70万」→(70,70), 「70-75」→(70,75), 「スキル見合い」→(None,None)
    # 「700000」→(70,70), 「〜80万」→(None,80)

def normalize_availability(value) -> str|None:
    # 「即日」→"即日", 「来月」→"2026-07", 「7月〜」→"2026-07"
```
- structurer.pyの後処理で適用
- rate_max < rate_min → swap + warning
- matcher.pyで正規化済み単価を優先使用

## ■4. 否定条件・除外条件の自動抽出（旧Task AS）
structurer.pyに _extract_must_not(body) 追加:
```python
MUST_NOT_PATTERNS = {
    "外国籍不可": [r"外国籍[：:]*不可", r"外国籍NG", r"日本国籍のみ"],
    "年齢制限": [r"(\d{2})歳まで", r"(\d{2})代まで"],
    "出社必須": [r"出社必須", r"フル出社", r"リモート不可", r"常駐必須"],
    "弊社要員不可": [r"弊社.*不可", r"プロパー不可"],
}
```
- case_json["must_not"]に保存
- matcher.py judge()で must_not チェック:
  - 外国籍不可 → 判断マニュアルv3 §1の除外ルール自動適用
  - 年齢制限超 → NG + 理由
  - 出社必須 → reasonsに追記

## テスト（各機能2-3件ずつ）
- email_cleaner: 署名除去、免責除去、引用除去
- 必須項目チェック: 全充足、部分欠落、再抽出
- normalizers: 単価パターン5種、稼働時期3種、逆転レンジ
- must_not: 外国籍不可検出、年齢制限検出、出社必須検出
- judge()でmust_not NG判定が動作すること

## 禁止
- CostGuardなしでLLMを呼び出さない（再抽出もCostGuard経由）
- 既存のNG/MATCH判定を緩めない
- skill_aliases.jsonを変更しない
