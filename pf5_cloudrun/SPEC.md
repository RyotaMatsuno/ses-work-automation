# SPEC.md - Phase5 Cloud Run LLM_KILL実装

## 目的
cost_guard.pyが発動してLLM_KILL=1をCloud Run環境変数に設定したとき、
webhook_server.py と skill_extractor.py のLLM呼び出しをスキップさせる。
これによりCloud Run側のコスト制御を完結させる。

## 背景
- Phase1でcost_guard.pyに `gcloud run services update line-webhook --update-env-vars LLM_KILL=1` を実装済み
- 現在webhook_server.pyはLLM_KILLを見ていないため、Cloud Runが止まらない
- 変更箇所は2関数のみ（call_claude / analyze_skill_sheet）

## 実装仕様

### 変更1: webhook_server.py - call_claude関数
**場所**: Line 166付近 `def call_claude(system, user_msg, max_tokens=120, caller="unknown"):`

**変更内容**: 関数の先頭にLLM_KILLチェックを追加する。
```python
def call_claude(system, user_msg, max_tokens=120, caller="unknown"):
    # [Phase5] LLM_KILLフラグチェック
    if os.environ.get("LLM_KILL", "0") == "1":
        print(f"[LLM_KILL] call_claude skipped (caller={caller})")
        return ""
    # 以下既存コード...
```

### 変更2: webhook_server.py - analyze_skill_sheet関数
**場所**: Line 1550付近（Sonnetを呼んでいるインライン requests.post）

この関数内の `requests.post("https://api.anthropic.com/v1/messages", ...)` の直前にチェックを追加。
返り値の型に合わせて `{}` または `None` を返す（既存の戻り値型を調査して合わせること）。

```python
# [Phase5] LLM_KILLフラグチェック
if os.environ.get("LLM_KILL", "0") == "1":
    print("[LLM_KILL] analyze_skill_sheet skipped")
    return {}
```

### 変更3: skill_extractor.py - LLM呼び出し箇所
skill_extractor.py内のLLM呼び出し（anthropic clientまたはrequests.post）の先頭にも同様のチェックを追加。
戻り値は既存の型に合わせる（Noneまたは空dict/空文字列）。

## 実装後の確認
1. syntax確認: `python -c "import py_compile; py_compile.compile('line_webhook/webhook_server.py', doraise=True); py_compile.compile('line_webhook/skill_extractor.py', doraise=True); print('ALL OK')"`
2. ローカル動作確認: `LLM_KILL=1 python -c "import os; os.environ['LLM_KILL']='1'; ..."`（Windows環境ではenv変数セットしてfunctionをimportしてcall_claude呼び出しがスキップされることを確認）

## gcloudデプロイコマンド（ジョブズが確認後に手動実行）
```
gcloud run deploy line-webhook --source=. --region=asia-northeast1 --max-instances=1 --timeout=60 --allow-unauthenticated
```
実行場所: `ses_work/line_webhook/` ディレクトリ

## 対象外
- Dockerfileは変更不要（LLM_KILLはCloud Run環境変数から自動で渡される）
- requirements.txtは変更不要
