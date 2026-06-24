# 【Cursor作業指示】Week2 Task C: pipeline CostGuard v2統合

対象ディレクトリ: ses_work/mail_pipeline/
作業内容: pipelineの全LLM経路をCostGuard v2に統合（CEO承認済み: fail-close方式）
完了条件: 全LLM呼び出しがCostGuard v2経由 + fail-close + テスト追加
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 修正1: call_claude()にCostGuard v2を統合

変更前: 独自$2/日制限（get_today_cost_usd）→ エラー時$0返却（暴走リスク）
変更後: CostGuard v2 の allowed() → finalize() を使用

```python
from common.cost_guard import allowed, finalize

def call_claude(prompt, system_prompt, max_tokens=1500):
    decision = allowed(
        block_type="mail_pipeline",
        phase="classify",
        estimated_input_tokens=len(prompt) // 4 + 200,
        estimated_output_tokens=max_tokens,
        model="claude-haiku-4-5-20251001"
    )
    if decision.exit_code != 0:
        log(f"CostGuard blocked: {decision.reason}")
        return ""
    try:
        response = client.messages.create(...)
        finalize(decision.claim_id, success=True,
                 actual_input_tokens=response.usage.input_tokens,
                 actual_output_tokens=response.usage.output_tokens)
        return response_text
    except Exception as e:
        finalize(decision.claim_id, transient=True)
        raise
```

## 修正2: Batch API経路にコスト記録追加
Batch完了後に record() でCostGuard v2に記録。投入前に allowed() でバジェット残量チェック。

## 修正3: 旧コスト管理コード削除
- get_today_cost_usd() → 削除
- DAILY_COST_LIMIT_USD = 2.0 → 削除
- log_cost() → CostGuard v2 の record() に置換

## テスト追加
- CostGuardブロック時にcall_claude()が空文字を返すこと
- Batch完了後にrecord()が呼ばれること
- 旧get_today_cost_usd()が存在しないこと

---

## 共通ルール
- 既存テスト全パス / 新規コードにtype hint
- CostGuard v2のインターフェースは変更しない
