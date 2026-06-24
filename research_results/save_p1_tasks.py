import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

base = os.path.join(os.environ["USERPROFILE"], "OneDrive", "\u30c7\u30b9\u30af\u30c8\u30c3\u30d7", "ses_work")
pending = os.path.join(base, "pending_tasks")

task_g = """# 【Cursor作業指示】Task G: インフラ設定（SQLite WAL + IMAP timeout）

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
"""

task_h = """# 【Cursor作業指示】Task H: LINE push修正 + UTC/JST境界修正

対象ディレクトリ: ses_work/
作業内容: LINE通知バグ修正 + コスト集計の日付整合
完了条件: push判定修正 + タイムゾーン統一 + テスト
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 修正1: LINE push残通数-1時のpush試行修正（#14）

### 対象ファイル
common/line_notify.py（またはpush_or_logがある場所）

### 問題
push_or_logでremaining != 0判定のため、quota取得失敗時(-1)にpush送信してしまう。

### 修正方針
```python
# 変更前
if remaining != 0:
    push_message(...)

# 変更後
if remaining > 0:
    push_message(...)
elif remaining == -1:
    log("LINE quota取得失敗 - pushスキップしてログのみ記録")
    log_message_to_file(...)
```

### reply-onlyモード追加
```python
REPLY_ONLY_THRESHOLD = 150

def push_or_log(user_id, message):
    remaining = get_remaining_push_count()
    if remaining == -1:
        log("quota取得失敗 - ログのみ")
        log_message_to_file(message)
        return False
    if remaining <= REPLY_ONLY_THRESHOLD:
        log(f"reply-onlyモード (残{remaining}通) - ログのみ")
        log_message_to_file(message)
        return False
    if remaining > 0:
        return push_message(user_id, message)
    return False
```

### テスト
- remaining=-1: pushしない、ログ記録
- remaining=100（<150）: pushしない、ログ記録
- remaining=180（>150）: push実行
- remaining=0: pushしない

---

## 修正2: UTC/JST日付境界不整合（#20）

### 問題
cost_guardのdaily_stateはUTC基準、pipeline Layer2集計はJST基準。
UTC 00:00〜08:59（JST 09:00〜17:59）の間で日付がずれる。

### 対象ファイル
common/cost_guard.py のdaily_state読み書き

### 修正方針
cost_guard内の日付処理をJSTに統一:

```python
from datetime import timezone, timedelta

JST = timezone(timedelta(hours=9))

def _today_jst() -> str:
    from datetime import datetime
    return datetime.now(JST).strftime("%Y-%m-%d")
```

daily_stateのdate列に入れる値を _today_jst() に変更。
既存の date("now") や strftime をすべて _today_jst() に置換。

### 注意
- 既存のdaily_stateデータはUTC基準で記録されている
- 切替日に1日分のコストが分割される可能性があるが、累計には影響しない
- monthly_stateも同様にJSTに統一

### テスト
- JST 2026-06-19 08:00（UTC 2026-06-18 23:00）→ daily_stateの日付が2026-06-19
- JST 2026-06-19 00:30（UTC 2026-06-18 15:30）→ daily_stateの日付が2026-06-19

---

## 共通ルール
- 既存テスト全パス / 新規コードにtype hint
"""

task_i = """# 【Cursor作業指示】Task I: パーサー改善（備考日数分岐 + human_reviewキーワード）

対象ディレクトリ: ses_work/
作業内容: マッチング精度改善 + ゲートチェッカー精度改善
完了条件: 日数分岐実装 + キーワード追加 + テスト
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 修正1: 備考フォールバック結果待ち日数分岐（#11）

### 対象ファイル
matching_v3/matcher.py の _calc_parallel_score()

### 問題
結果待ちスコアが2.0固定。判断マニュアルの分岐が効いていない:
- 結果待ち(1-2日): 2.5
- 結果待ち(3-7日): 2.0
- 結果待ち(8日+): 0

### 修正方針
備考テキストから結果待ち日数を推定するパーサーを追加:

```python
import re
from datetime import datetime, timedelta

def _extract_result_wait_days(remark: str) -> int | None:
    \"\"\"備考テキストから結果待ち日数を推定\"\"\"
    # パターン1: 「結果待ち 6/15」「結果待ち（6月15日）」
    m = re.search(r'結果待ち.*?(\d{1,2})[/月](\d{1,2})', remark)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        now = datetime.now()
        interview_date = now.replace(month=month, day=day)
        if interview_date > now:
            interview_date = interview_date.replace(year=now.year - 1)
        days = (now - interview_date).days
        return max(0, days)

    # パターン2: 「結果待ち」のみ（日付なし）→ 不明
    if '結果待ち' in remark:
        return None  # 不明→デフォルト2.0を維持

    return None

def _result_wait_score(days: int | None) -> float:
    if days is None:
        return 2.0  # 不明時はデフォルト
    if days <= 2:
        return 2.5
    if days <= 7:
        return 2.0
    return 0.0  # 8日以上はカウントなし
```

_calc_parallel_score() 内で「結果待ち」検出時に上記関数を呼ぶ。

### テスト
- 「結果待ち 6/18」（1日前）→ 2.5
- 「結果待ち 6/15」（4日前）→ 2.0
- 「結果待ち 6/1」（18日前）→ 0.0
- 「結果待ち」（日付なし）→ 2.0（デフォルト）

---

## 修正2: needs_human_review層1キーワード追加（#17）

### 対象ファイル
gate_checker/gate_check.py の needs_human_review()

### 問題
層1キーワードに「費用が発生」「契約変更」が未登録。
層3のHUMAN_REVIEW行欠落時のフォールバックなし。

### 修正方針
```python
LAYER1_KEYWORDS = [
    "費用が発生", "契約変更",  # 追加
    "岡本に連絡", "根本設計変更",
    "法人化", "TERRA依存",
    # 既存キーワード...
]

# 層3フォールバック追加
def needs_human_review(text: str) -> bool:
    # 層1: 完全一致キーワード
    for kw in LAYER1_KEYWORDS:
        if kw in text:
            return True
    # 層2: 類義語辞書
    for synonym, canonical in SYNONYM_MAP.items():
        if synonym in text and canonical in LAYER1_KEYWORDS:
            return True
    # 層3: GPT自己判定
    try:
        gpt_result = _gpt_human_review_check(text)
        if "HUMAN_REVIEW" in gpt_result:
            return True
    except Exception:
        # 層3失敗時のフォールバック: 安全側に倒す（要確認）
        return True
    return False
```

### テスト
- 「費用が発生します」→ True
- 「契約変更が必要」→ True
- 「コストが増える」（類義語）→ True（類義語辞書に「コスト」→「費用が発生」を追加）
- 層3失敗時→ True（安全側）

---

## 共通ルール
- 既存テスト全パス / 新規コードにtype hint
"""

task_j = """# 【Cursor作業指示】Task J: gate_checker v2.2 + スケジューラ統廃合

対象ディレクトリ: ses_work/
作業内容: ゲートチェッカー改善 + スケジューラ一本化
完了条件: Gemini復旧 + プロンプト改善 + scheduler.py廃止 + テスト
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 修正1: gate_checker Geminiフォールバック問題調査＋修正（#13）

### 調査手順
1. gate_checker/results/ の最新JSONからGeminiのエラー詳細を確認
2. gate_check.py のGemini呼び出し箇所でHTTPステータスを記録

### 考えられる原因（優先順で調査）
1. レート制限: DAILY_CALL_LIMIT=10 → SPECの30に修正
2. モデル名: gemini-2.0-flashが利用可能か確認
3. APIキー: GEMINI_API_KEY環境変数の有効性確認

### 修正箇所
gate_check.py:
- DAILY_CALL_LIMIT = 10 → 30 に修正
- Gemini呼び出しにtry/except追加、エラー時にHTTPステータス+bodyをログ出力
- Geminiレスポンスのパース処理を堅牢化（空レスポンス対応）

### システムプロンプト改善
GPTがNotion APIにCostGuardを誤要求する問題の対策:

gate_check.py のシステムプロンプトに以下を追加:
```
## 重要な注意事項
- CostGuardはLLM API呼び出し（OpenAI/Anthropic/Gemini）専用です
- Notion API、freee API、LINE Messaging API等の非LLM外部APIはCostGuard対象外です
- Notion DBへの読み書きは「自動送信」には該当しません（DB操作は確認不要）
```

### テスト
- DAILY_CALL_LIMIT=30が反映されていること
- Geminiエラー時にHTTPステータスがログに出力されること
- Notion APIを含むコードでCostGuard指摘が出ないこと（プロンプト改善確認）

---

## 修正2: スケジューラ二重共存の解消（#18）

### 方針: Python scheduler.pyを廃止、Task Schedulerに一本化

### 理由
- Task Schedulerは既にOS起動時自動実行・失敗時リスタート・ログ付きで安定稼働中
- scheduler.pyを残すとpythonプロセス管理が追加で必要
- Task Schedulerは他タスク（importer, watchdog等）と統一管理できる

### 修正手順
1. scheduler.py の先頭に廃止メッセージを追加:
```python
print("このスクリプトは廃止されました。Windows Task Schedulerを使用してください。")
sys.exit(0)
```

2. scheduler.pyから起動されていたタスクがTask Schedulerに登録済みか確認:
   - SES_MailPipeline → 登録済み
   - その他のジョブ → 未登録なら追加

3. ファイルロックによる二重起動防止:
mail_pipeline.pyの先頭に追加:
```python
import msvcrt

LOCK_FILE = os.path.join(os.environ.get("LOCALAPPDATA", ""), "ses_work_state", "pipeline.lock")

def acquire_lock():
    os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
    lock_fh = open(LOCK_FILE, 'w')
    try:
        msvcrt.locking(lock_fh.fileno(), msvcrt.LK_NBLCK, 1)
        return lock_fh
    except IOError:
        log("別プロセスが実行中 - スキップ")
        sys.exit(0)
```

### テスト
- scheduler.py実行時に即終了すること
- ファイルロック取得済みで2つ目のプロセスがexit 0すること

---

## 共通ルール
- 既存テスト全パス / 新規コードにtype hint
"""

tasks = {
    "20260619_190000_taskG_sqlite_wal_imap.md": task_g,
    "20260619_190100_taskH_line_push_utc_jst.md": task_h,
    "20260619_190200_taskI_parser_humanreview.md": task_i,
    "20260619_190300_taskJ_gatechecker_scheduler.md": task_j,
}

for fname, content in tasks.items():
    fpath = os.path.join(pending, fname)
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"saved: {fname}")

print(f"\n合計 {len(tasks)} タスクを pending_tasks/ に保存完了")
for f in sorted(os.listdir(pending)):
    if f.startswith('2026'):
        size = os.path.getsize(os.path.join(pending, f))
        print(f"  {f} ({size:,} bytes)")
