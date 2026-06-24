# SPEC - 案件側マッチング詳細照会

## 背景
- 人員側: 「HS 北小金」→ マッチング案件一覧 → 「詳細 ①」→ 案件全文 ✅
- 案件側: 「案件名」→ マッチング人員一覧 → 「詳細 ①」→ ❌ 未実装（_LAST_RESULTSが案件キャッシュのみ）

## 修正対象
ファイル: line_webhook/line_query.py

## 修正内容

### 1. キャッシュを人員側・案件側で分離
現在: _LAST_RESULTS = {}  # 案件リストしかキャッシュされていない

変更後:
_LAST_ENG_RESULTS = {}   # 案件名クエリ時のエンジニア結果キャッシュ
                          # key=案件名 value=matched_engsリスト（辞書: {page, gross_profit}）
_LAST_PROJ_RESULTS = {}  # 人員クエリ時の案件結果キャッシュ（既存の_LAST_RESULTS）
                          # key=イニシャル value=matched_projsリスト

### 2. project_query()でエンジニアキャッシュを保存
project_query()の末尾（format_engineer_result呼び出し前）に追加:
  _LAST_ENG_RESULTS["latest"] = matched_engs  # ← 追加
  return format_engineer_result(project, matched_engs)

### 3. detail_query()を人員側・案件側両対応に拡張
現在: _LAST_RESULTSから案件を取得してformat
変更後:
  1. _LAST_ENG_RESULTSに"latest"がある場合 → エンジニア詳細として返す
  2. _LAST_PROJ_RESULTSに"latest"がある場合 → 案件詳細として返す（既存動作）
  3. 両方ある場合は直近のクエリ種別で判定

### 4. エンジニア詳細フォーマット（新規）
format_engineer_detail(eng_item, idx) -> str:
  eng = eng_item["page"]
  fields:
  - 【詳細 {num}】{名前}｜{最寄り駅}
  - スキル: {スキル}
  - 稼働: {稼働状況} / 単価: {単価}万 / 粗利: {粗利}万
  - 稼働可能: {稼働可能日} / 鮮度: {business_days_since}日前
  - 所属: {所属会社名} / {所属担当者名} / {所属メール}
  - 【人員情報原文】（※「人員情報原文」フィールドがある場合のみ）
  - {人員情報原文全文}
  - 📎 スキルシート：{DriveリンクURL}（※「DriveリンクURL」フィールドがある場合のみ）

### 5. 最後のクエリ種別を記憶
_LAST_QUERY_TYPE = ""  # "engineer" or "project"
classify_query()の結果をhandle_line_query()でセットする

## 実装制約
- 既存の人員側（HS 北小金 → 詳細 ①）の動作を壊さないこと
- encoding='utf-8'・flush=True必須
- DRY_RUN非依存（Notion読み取りのみなので問題なし）
- バックアップ: line_query.py.bak_0602を先に作成


---

## 追加修正: classify_queryのバグ修正

### 問題
「Oracle DBマイグレーション」のような英語始まりの案件名が
engineer（イニシャル判定）に誤分類される。

現在の正規表現: ^([A-Za-z.]{1,8})[\s\u3000/]+(.+)$
→ "Oracle" は1〜8文字の英字なので誤マッチする

### 修正方法
イニシャル判定の条件を厳密化する:
- イニシャル部分は最大4文字（"HS", "H.S", "TK", "KY"等）
- 5文字以上の英字は案件名として扱う
- 具体的には正規表現を ^([A-Za-z.]{1,4})[\s\u3000/]+(.+)$ に変更

または判定ロジックを変更:
- イニシャル候補の文字数が5文字以上の場合はproject判定に倒す

### テストケース（修正後に全パスすること）
- "HS 北小金" → engineer {initial: "HS", station: "北小金"} ✅
- "H.S 北小金" → engineer {initial: "HS", station: "北小金"} ✅
- "TK 渋谷" → engineer {initial: "TK", station: "渋谷"} ✅
- "Oracle DBマイグレーション" → project {name: "Oracle DBマイグレーション"} ← 修正
- "Java Spring案件 渋谷" → project {name: "Java Spring案件 渋谷"} ← 修正
- "某金融系Java開発" → project ✅
