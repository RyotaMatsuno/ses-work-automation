# SPEC: notify_line.py 2点修正

## 修正1: 1案件1通に集約（通知数削減）

### 現状
候補者1人につき1通送信 → 12案件×複数名 = 80通

### 変更後
1案件につき1通にまとめる。1通の中に候補者全員を列挙する。

### メッセージフォーマット（案件単位）
```
【マッチング結果】
案件: {project_name}
業務内容: {project_detail}（案件の詳細情報をそのまま記載）
必須: {required_skills}
尚可: {optional_skills}
単価: {price}万円
稼働: {start_date}
──────────────
▶ {engineer_name}（スコア: {score}）
  単価: {price}万円 / 稼働: {available_date}
  スキル: {skills（全スキルをカンマ区切り）}
  必須判定: {required_judgement}
  尚可判定: {optional_judgement}

▶ {engineer_name2}（スコア: {score2}）
  ...（以下同様）
──────────────
意向確認をお願いします。
```

### 変更点
- `for candidate in candidates` のループをやめ、案件単位で1メッセージを組み立てる
- 候補者は全員列挙（上限なし）

---

## 修正2: 案件情報・人員情報をそのまま貼る

### 案件情報
- result.jsonの `project_name` だけでなく、Notionから案件の詳細情報を取得して本文に含める
- 取得するフィールド: 案件名、必須スキル、尚可スキル、単価、開始日
- result.jsonのitemに `project_id` があるのでそこからNotionページを取得する

### 人員情報
- エンジニアのNotionページから以下を取得して本文に含める
  - 名前、スキル（多値）、単価、稼働可能日
- result.jsonの `engineer_id` からNotionページを取得する
- スキルは `skills` フィールド（multi_select）からカンマ区切りで表示

### 実装方針
- Notion API呼び出しはキャッシュ済みの `assignee_cache` と同様に `info_cache` を別途用意する
- `get_page_info(page_id, headers)` 関数を新規作成
  - 案件ページ → 案件名/必須/尚可/単価/開始日 を返す
  - エンジニアページ → 名前/スキルリスト/単価/稼働日 を返す

---

## 修正対象ファイル
`matching_v2/notify_line.py`

## 変更禁止
- `--dry-run` オプションの挙動は維持する
- `build_line_accounts()` のチャンネルトークン割り当て（松野公式チャンネルから送信）は変更しない
- 担当者クロス通知ロジック（`build_notifications`）の基本構造は維持する

## TASKS
- [x] `get_page_info(page_id, headers, page_type)` 関数を追加（page_type: "project" or "engineer"）
- [x] 案件単位でメッセージを組み立てる `build_project_message()` に変更
- [x] dry-run / 本番送信ともに1案件1通になるようmainループを修正
- [x] 送信済みカウントを「案件数」ベースに変更
