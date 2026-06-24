# CLAUDE.md — matching_v3 実装ルール（Codex用）

最終更新: 2026-06-03
**このファイルを最初に読み、SPEC.md の仕様通りに TASKS.md の順番で実装すること。**

---

## ディレクトリ構成

```
ses_work/matching_v3/
├── CLAUDE.md              ← このファイル
├── SPEC.md                ← 仕様書（必ず読む）
├── TASKS.md               ← 実装チェックリスト（完了時 [ ]→[x] に更新）
├── skill_aliases.json     ← スキル辞書（変更禁止）
├── users.yaml             ← LINE user_id 等の設定
├── matching_v3.py         ← メインエントリポイント
├── structurer.py          ← LLM呼び出し（構造化のみ）
├── matcher.py             ← Pythonマッチングロジック
├── notifier.py            ← LINE通知
├── cost_guard.py          ← コスト監視
├── processed_db.py        ← 処理ステータスDB（SQLite）
├── notion_client.py       ← Notion REST APIラッパー
├── config.py              ← 設定ロード
├── tests/
│   ├── test_processed_db.py
│   ├── test_cost_guard.py
│   ├── test_structurer.py
│   ├── test_matcher.py
│   └── fixtures.json      ← テスト用ダミーデータ
└── logs/                  ← 実行時に自動生成
```

---

## 設定・認証

```python
# config.py 経由で全キーを読む（直接 dotenv_values を呼ばない）
from config import Config
cfg = Config()
```

- キーは全て `ses_work/config/.env` から `dotenv_values()` で読む
- ハードコード禁止: APIキー・Notion DB ID・LINE user_id・モデル名
- Notion DB ID は config.py の定数として定義
- LINE user_id は `users.yaml` から読む
- モデル名は config.py で定義、環境変数 `STRUCTURER_MODEL` でオーバーライド可

---

## 重大ルール（絶対に違反しない）

### 1. PII境界: エンジニアの個人情報を LLM に渡さない
- `structurer.py` が LLM に渡すのは案件メール本文のみ
- エンジニアの名前・単価・スキルは Python レイヤーで完結させる
- `matcher.py` でのLLM呼び出し禁止

### 2. ローカルJSONL先書き → Notion後同期
- LLM構造化結果はまず `logs/structured.jsonl` に保存
- Notion書き込みが失敗しても JSONL データは残す
- `processed_db` のステータスは JSONL 保存後に更新する

### 3. 全 API 呼び出し前にコスト確認
```python
if not cost_guard.can_call(est_input_tokens, est_output_tokens):
    logger.warning("Cost limit reached, skipping")
    return
```

### 4. processed_db 経由でステータス管理
- 全案件は `processed_db.py` でステータス管理
- `api_called=True` にしてから API を呼ぶ（エラーでも記録が残る）
- 開始前に `is_processed()` で重複チェック

### 5. 平日のみ稼働
```python
import jpholiday
from datetime import date
if date.today().weekday() >= 5 or jpholiday.is_holiday(date.today()):
    logger.info("非稼働日のためスキップ"); sys.exit(0)
```

---

## 禁止事項

- `ses_work/mail_pipeline.py` の変更（別システム、触らない）
- `ses_work/matching_v2/` の変更（旧システム、触らない）
- `skill_aliases.json` の変更（スキル辞書更新は松野承認が必要）
- LINE Push 通知を 1 日 8 通超で送信
- Notion DBへ LLM 結果を直接書き込む（JSONL を経由すること）
- `git commit` / `git push`
- requirements.txt 未記載の外部ライブラリ追加
  - 許可済み: `anthropic`, `python-dotenv`, `requests`, `jpholiday`, `PyYAML`, `pytest`, `sqlite3`（stdlib）

---

## コーディング規約

- Python 3.12+、型ヒント必須
- ログ: 各ファイルで `logging.getLogger(__name__)` を使う
  - ファイル出力: `matching_v3/logs/matching_v3_YYYYMMDD.log`
  - stdout: WARNING 以上
- エラーハンドリング: 例外を握りつぶさない
  - Notion API エラー → ログ + processed_db に ERROR ステータス → 次のケースへ継続
  - Anthropic API エラー → ログ + cost_guard に記録 → REVIEW 扱いで通知
- タイムゾーン: `datetime.now(timezone(timedelta(hours=9)))` (JST)
- 文字コード: UTF-8 統一
- テスト: `pytest`、主要ロジックはモックを使った単体テストを書く

---

## 参照ファイル

| ファイル | 用途 |
|---|---|
| `ses_work/config/.env` | APIキー |
| `matching_v3/users.yaml` | LINE user_id 等の設定 |
| `matching_v3/skill_aliases.json` | スキル正規化辞書（31語彙） |
| `ses_work/usage_tracker/cost_log.jsonl` | 既存コストログ（追記） |
| `ses_work/matching_v2/matching_v2.py` | 旧実装（参考のみ） |

---

## テスト実行

```bash
cd ses_work/matching_v3
pytest tests/ -v
```
