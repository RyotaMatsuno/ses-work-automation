# 【Cursor作業指示】Task S: 既存データバックフィル + マッチングガード

対象ディレクトリ: ses_work/
作業内容: (1) 案件/エンジニアDBの既存レコードにskills/price再抽出 (2) マッチングにガード追加
完了条件: 案件no_skills 57%→35%以下 + マッチングにスキル0/異常単価ガード
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## Part 1: 案件DBバックフィル

### 概要
Notion案件DB(募集中617件)の57%がスキル未設定、47%が単価未設定。
raw_inbox.dbに元メール原文が保存されているので、ルールベースで再抽出してNotionに書き戻す。

### 新規スクリプト: backfill_projects.py

処理フロー:
1. Notion案件DBから募集中で skills空 or price空 のレコードを取得
2. 各レコードの元MessageIDでraw_inbox.dbから原文取得
3. price_extractor.py / skill_extractor.py で再抽出
4. 空だった項目のみNotionに書き戻し（既存値は上書きしない）
5. 処理結果をログ出力

### Notion API
- GET: POST /v1/databases/{PROJECT_DB}/query でフィルタ
- UPDATE: PATCH /v1/pages/{page_id} でプロパティ更新
- 必要スキル: multi_select形式（{name: "Java"}）
- 単価（万円）: number形式
- Notion-Version: 2022-06-28
- Rate limit: 0.3秒/リクエスト

### 安全ルール
- 既に値がある項目は上書きしない
- price_extractor結果のconfidence=suspiciousは書き込まない
- DRY_RUN=1モード必須（デフォルト: ログ出力のみ、書き込みなし）
- CostGuardは不要（LLM呼び出しなし、ルールベースのみ）
- 処理件数の上限: 100件/run

### 元MessageIDの取得
Notion案件DBの「元MessageID」プロパティ(rich_text)にraw_inbox.dbのmessage_idが入っている。
```python
msg_id = props.get("元MessageID", {}).get("rich_text", [])
msg_id_text = msg_id[0].get("text", {}).get("content", "") if msg_id else ""
```

---

## Part 2: マッチングガード

### webhook_server.py のrun_reverse_matching修正

#### ガード1: スキル0件エンジニアの制限
```python
if not eng_skills:
    # スキル0件 → スキルありの案件のみマッチ（スキルなし案件は除外）
    # 粗利のみでマッチングすると全案件にマッチするため
    pass  # 後述のスコア計算でskill_pts=0になるので結果的に低スコア
```

#### ガード2: 異常単価の除外
```python
if eng_price > 200 or (eng_price > 0 and eng_price < 15):
    return {"matches": [], "stats": {"error": "engineer_price_anomaly"}}
```

#### ガード3: マッチ件数の上限
```python
# 上位20件のみ返す（300件返しても使えない）
matches = sorted(matches, key=score, reverse=True)[:20]
```

### line_query.py にも同様のガード追加

---

## Part 3: バックフィル後の検証

### verify_backfill.py
1. Notion案件DBの skills/price 埋まり率を計測
2. 目標: No skills 57%→35%以下、No price 47%→25%以下
3. マッチングシミュレーション再実行（10名ランダム）

---

## 実装順序
1. backfill_projects.py 作成
2. DRY_RUN=1 で実行、ログ確認
3. webhook_server.py にガード追加
4. line_query.py にガード追加
5. verify_backfill.py で検証
6. DRY_RUN=0 で本番実行（松野確認後）

## 禁止事項
- 既存値を上書きしない（空欄のみ埋める）
- Notion DBスキーマ変更しない
- LLMを使わない（ルールベースのみ）
- CostGuard迂回しない（LLM不使用なので該当せず）
