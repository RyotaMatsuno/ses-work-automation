# 【Cursor作業指示】Task G: インフラ設定（SQLite WAL + IMAP timeout）

対象ディレクトリ: ses_work/
作業内容: DB安定性強化 + メール接続の安定化
完了条件: WAL設定 + timeout/リトライ追加 + テスト
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 修正1: SQLite WALモード設定（#12）

### 対象ファイル
1. mail_pipeline/raw_inbox.py — raw_inbox.db接続時
2. common/cost_guard.py — state.sqlite3接続時

### 修正方針
各ファイルのSQLite接続直後に以下を追加:
```python
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA busy_timeout=5000")  # 5秒待ち
```

### 注意
- WALモードは一度設定すると永続化される（再起動後も維持）
- busy_timeout追加で並列アクセス時のdatabase is lockedエラーを軽減
- 既存データは保持される（マイグレーション不要）

### テスト
- WAL設定後にPRAGMA journal_modeがwalを返すこと
- 2スレッドから同時書き込みしてもエラーにならないこと

---

## 修正2: IMAP接続タイムアウト + リトライ（#19）

### 対象ファイル
mail_pipeline/mail_pipeline.py のIMAP接続箇所

### 修正方針
変更前:
```python
mail = imaplib.IMAP4_SSL(IMAP_SERVER)
```

変更後:
```python
import socket

IMAP_TIMEOUT = 30  # 秒
IMAP_MAX_RETRIES = 3

def connect_imap():
    for attempt in range(IMAP_MAX_RETRIES):
        try:
            socket.setdefaulttimeout(IMAP_TIMEOUT)
            mail = imaplib.IMAP4_SSL(IMAP_SERVER)
            mail.login(IMAP_USER, IMAP_PASS)
            return mail
        except (socket.timeout, imaplib.IMAP4.error, OSError) as e:
            log(f"IMAP接続失敗 ({attempt+1}/{IMAP_MAX_RETRIES}): {e}")
            if attempt < IMAP_MAX_RETRIES - 1:
                import time
                time.sleep(5 * (attempt + 1))  # 5, 10, 15秒待ち
            else:
                raise
        finally:
            socket.setdefaulttimeout(None)  # グローバル設定を戻す
```

### テスト
- タイムアウト設定が効くこと（モックで確認）
- 3回リトライ後にraiseされること

---

## 共通ルール
- 既存テスト全パス / 新規コードにtype hint
