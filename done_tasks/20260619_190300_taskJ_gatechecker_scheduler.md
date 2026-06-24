# 【Cursor作業指示】Task J: gate_checker v2.2 + スケジューラ統廃合

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
