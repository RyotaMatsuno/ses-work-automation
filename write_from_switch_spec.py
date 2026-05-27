spec = """# SPEC.md - メール送信Fromアドレス切り替え

最終更新: 2026-05-26

## 概要
提案メール・意向確認メール送信時のFromアドレスを案件担当者に合わせて切り替える。
- 松野担当案件 → r-matsuno@terra-ltd.co.jp から送信
- 岡本担当案件 → r-okamoto@terra-ltd.co.jp から送信
- 担当者不明 → sessales@terra-ltd.co.jp から送信（デフォルト）

## 対象ファイル
- ses_work/mail_pipeline/mail_pipeline.py
- ses_work/mail_mcp/mail_server.py（accountパラメータを確認）

## 実装
mail_pipeline.pyの送信処理に以下を追加:

```python
def get_from_account(owner: str) -> str:
    if owner and '松野' in owner:
        return 'matsuno'
    elif owner and '岡本' in owner:
        return 'okamoto'
    return 'sessales'
```

- メール送信時に `get_from_account(project_owner)` でアカウントを決定
- ses-mail MCPの `send_email(account=..., ...)` のaccountに渡す

## 完了条件
1. py_compile mail_pipeline/mail_pipeline.py → エラーなし
2. get_from_account('松野') → 'matsuno'
3. get_from_account('岡本') → 'okamoto'
4. get_from_account('') → 'sessales'
"""

tasks = """# TASKS.md - メール送信Fromアドレス切り替え

- [ ] 1. mail_pipeline.py: get_from_account(owner)関数を追加
- [ ] 2. mail_pipeline.py: メール送信呼び出し箇所でget_from_account()を使用してアカウントを切り替え
- [ ] 3. py_compile mail_pipeline/mail_pipeline.py → エラーなし
- [ ] 4. get_from_account単体テスト（松野/岡本/空の3ケース）
"""

claude_md = """# CLAUDE.md - Fromアドレス切り替え

## 禁止事項
- 既存の送信ロジックを壊さない
- ses-mail MCPのAPI仕様を変えない

## ルール
- accountは 'matsuno' / 'okamoto' / 'sessales' の3択のみ
"""

import os
base = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\from_switch_spec'
os.makedirs(base, exist_ok=True)
open(os.path.join(base,'SPEC.md'),'w',encoding='utf-8').write(spec)
open(os.path.join(base,'TASKS.md'),'w',encoding='utf-8').write(tasks)
open(os.path.join(base,'CLAUDE.md'),'w',encoding='utf-8').write(claude_md)
print("Fromスイッチ 3点セット完了")
