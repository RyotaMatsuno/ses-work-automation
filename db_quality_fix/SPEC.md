# SPEC.md — エンジニアDB クレンジング仕様書

バージョン: v1.2（GPT-4o設計レビュー反映）
作成日: 2026-06-10
設計: ジョブズ

---

## 1. 検出パターン（P1〜P7）

### P1: 外国籍で提案対象フラグ=True（絶対除外違反）
- 条件: `国籍 in NATIONALITY_BLOCK` AND `提案対象フラグ == True`
- NATIONALITY_BLOCK: `{"外国籍", "外国籍候補", "海外籍", "日本国籍以外"}`
- アクション: `提案対象フラグ → False`、`除外理由` に `"P1:外国籍（自動クレンジング）"` を追記
- 重要度: 🔴 Critical

### P2: 国籍=要確認で提案対象フラグ=True
- 条件: `国籍 in NATIONALITY_UNKNOWN` AND `提案対象フラグ == True`
- NATIONALITY_UNKNOWN: `{"要確認", "不明", "未確認", "", None}`
- アクション: `提案対象フラグ → False`、`除外理由` に `"P2:国籍要確認（要人工確認）"` を追記
- 重要度: 🔴 Critical

### P3: 経験年数の異常値（パース誤り）
- 条件:
  - `経験年数 < 0` → 確実に異常
  - `経験年数 > 45` → null化
  - `36 <= 経験年数 <= 45` → warning のみ
  - 年齢フィールドがある場合: `経験年数 > 年齢 - 15` → null化（例: 年齢30・経験20は異常）
- アクション（null化対象）: `経験年数 → null`、`備考（LINEメモ）` 末尾に `\n[cleaner:P3:{日付}] 経験年数異常値 {元の値} をnull化` を追記
- idempotency: `[cleaner:P3:` が備考に既にあればスキップ
- 重要度: 🟠 High（null化対象）/ 🟡 Warning（36〜45）

### P4: 稼働可能日が過去日付（古すぎる）
- 条件:
  - `稼働可能日 < today - 180日` → null化
  - `稼働可能日 > today + 365日` → warning のみ（未来すぎる）
- アクション（null化対象）: `稼働可能日 → null`、備考末尾に `\n[cleaner:P4:{日付}] 稼働可能日異常値 {元の値} をnull化` を追記
- idempotency: `[cleaner:P4:` が備考に既にあればスキップ
- 重要度: 🟠 High（180日超過去）/ 🟡 Warning（365日超未来）

### P5: 名前がプレースホルダ
- 条件: 名前プロパティが PLACEHOLDER_NAMES に完全一致
  ```python
  PLACEHOLDER_NAMES = {
      "名前", "氏名", "開発太郎", "開発 太郎", "山田太郎",
      "テスト", "test", "サンプル", "sample", "N/A", "不明", "人材", "エンジニア"
  }
  ```
- 追加チェック: 名前に「案件」「募集」「株式会社」「要員情報」が含まれる場合も対象
- アクション: `提案対象フラグ → False`、`除外理由` に `"P5:プレースホルダ名（要確認）"` を追記
- 重要度: 🟠 High

### P6: 案件メールが人材DBに混入（スコア制）
- スコア計算:
  ```python
  HIGH_SIGNAL = [
      "案件名", "案件：", "■案件内容", "作業内容", "業務内容",
      "募集人数", "商流", "精算", "面談回数", "貴社まで", "契約期間", "契約形態"
  ]
  MEDIUM_SIGNAL = [
      "必要スキル：", "■担当工程：", "■必須スキル", "尚可スキル",
      "作業場所", "■単価：", "勤務地", "リモート頻度", "外国籍可否"
  ]
  score = (HIGH_SIGNALの一致数 × 2) + (MEDIUM_SIGNALの一致数 × 1)
  ```
- 判定:
  - score 0〜1 → 正常
  - score 2〜3 → warning のみ（フラグ変更しない）
  - score 4以上 → `提案対象フラグ → False`、`除外理由` に `"P6:案件メール誤登録（score={N}）"` を追記
- idempotency: `[cleaner:P6:` が除外理由に既にあればスキップ
- 重要度: 🟠 High（score 4以上）/ 🟡 Warning（score 2〜3）

### P7: 単価が未設定（null）かつ提案対象フラグ=True
- 条件: `単価（万円） == null` AND `提案対象フラグ == True`
- 追加: 単価 < 20 または 単価 > 150 も warning（桁・単位ミス疑い）
- アクション: 変更なし、レポートに警告記載のみ
- 重要度: 🟡 Warning

---

## 2. 安全装置

### バックアップ
- dry_run・live 実行前に必ず対象レコードの全プロパティを保存
- 保存先: `output/backup_YYYYMMDD_HHMMSS.jsonl`
- 形式: 1行1レコード、page_id と全プロパティのJSON

### 更新件数上限
- デフォルト: `--max-updates 50`
- 初回推奨: `--max-updates 10` で動作確認してから全件実行

### パターン指定実行
- `--patterns P1,P2` で特定パターンのみ実行可能
- デフォルト: 全パターン

### idempotency
- 備考・除外理由に `[cleaner:Pn:YYYY-MM-DD]` が既にあればそのパターンはスキップ
- 同じスクリプトを複数回実行しても備考が増殖しない

### Notion APIラッパー（必須実装）
```python
def notion_request(method, url, max_retries=5, **kwargs):
    for attempt in range(max_retries):
        res = requests.request(method, url, timeout=30, **kwargs)
        if res.status_code == 429:
            retry_after = int(res.headers.get("Retry-After", "1"))
            time.sleep(retry_after + 0.5)
            continue
        if 500 <= res.status_code < 600:
            time.sleep(2 ** attempt)
            continue
        res.raise_for_status()
        return res
    raise RuntimeError(f"Notion API retry exhausted: {url}")
```
- query呼び出し後: `time.sleep(0.35)`
- update呼び出し後: `time.sleep(0.5)`

---

## 3. Notionプロパティ名の定数化
```python
PROP = {
    "name":           "名前",
    "target_flag":    "提案対象フラグ",
    "nationality":    "国籍",
    "experience":     "経験年数",
    "available_date": "稼働可能日",
    "remarks":        "備考（LINEメモ）",
    "exclude_reason": "除外理由",
    "raw_info":       "人員情報原文",
    "rate":           "単価（万円）",
    "age":            "年齢",
}
```
- 起動時にDBスキーマを取得し、PROP の全キーが存在しない場合は即終了

---

## 4. スクリプト構成

```
db_quality_fix/
├── CLAUDE.md
├── SPEC.md（本ファイル）
├── TASKS.md
├── cleaner.py          # メインスクリプト
├── output/
│   ├── backup_YYYYMMDD_HHMMSS.jsonl   # 更新前データバックアップ
│   ├── report_YYYYMMDD_HHMMSS.txt     # 人間が読むレポート
│   └── report_YYYYMMDD_HHMMSS.json    # 構造化レポート
```

---

## 5. CLI仕様

```
python cleaner.py [--live] [--patterns P1,P2,...] [--max-updates N] [--db-id ID]
```

- `--live`: Notionを実際に更新（デフォルト: dry_run）
- `--patterns`: 実行するパターン（デフォルト: P1,P2,P3,P4,P5,P6,P7）
- `--max-updates`: 1回の実行で更新できる最大件数（デフォルト: 50）
- `--db-id`: エンジニアDB IDを上書き

---

## 6. 推奨実行順序

```
1. python cleaner.py --patterns P1,P2,P5          # dry_run で件数確認
2. python cleaner.py --patterns P1,P2,P5 --live --max-updates 10  # 少量でlive確認
3. python cleaner.py --patterns P1,P2,P5 --live   # 全件live
4. python cleaner.py --patterns P3,P4             # dry_run 確認
5. python cleaner.py --patterns P3,P4 --live --max-updates 10
6. python cleaner.py --patterns P6                # dry_run でスコア分布確認
7. python cleaner.py --patterns P6 --live         # score 4以上のみFalse化
```

---

## 7. 将来フェーズ（本タスクのスコープ外）

### フェーズ2: validators/ 共通モジュール化
- `validators/engineer_rules.py`: P1〜P7のロジックを共通化
- `validators/normalizers.py`: 単価・稼働日・国籍の正規化
- mail_pipeline.py の取込時バリデーションに適用

### フェーズ2追加パターン（GPT-4oレビューより）
- P8: 年齢の異常値（<18 または >75）
- P9: 単価の桁ミス（>10000で円単位疑い）
- P10: 稼働可能日の未来すぎる値（today+365日超）→ v1.2でwarningのみ対応済み
- P11: 名前の追加異常パターン（メール件名混入等）→ v1.2で一部対応済み
- P12: 備考にメールアドレス・電話番号・住所が混入
- P13: 国籍の表記ゆれ正規化テーブル拡充
- P15: 重複人材の検出
- P17: 提案対象=Trueなのに必須項目が2個以上null
