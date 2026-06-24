import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

p = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\CLAUDE.md")
content = p.read_text(encoding="utf-8")

old = """## 禁止事項

- **松野にファイルを検索・ダウンロードさせる**
- **CostGuardなしでLLMを呼び出す**
- **3点セット（CLAUDE.md/SPEC.md/TASKS.md）なしで実装を開始する**
- **ゲート①②なしでCloud Runにデプロイする**
- **draft-only制約（ジラード・渋沢）を破って送信・確定操作をする**
- **freee請求書の確定・削除を自律実行する**（松野がfreee UIで操作）
- **本番Notion DBを無確認で大量書き込みする**
- **GitHubにAPIキー・シークレットをコミットする**
- **日本語パスをcwdに直接渡す**"""

new = """## 禁止事項

- **松野にファイルを検索・ダウンロードさせる**
- **CostGuardなしでLLMを呼び出す**
- **3点セット（CLAUDE.md/SPEC.md/TASKS.md）なしで実装を開始する**
- **ゲート①②なしでCloud Runにデプロイする**
- **draft-only制約（ジラード・渋沢）を破って送信・確定操作をする**
- **freee請求書の確定・削除を自律実行する**（松野がfreee UIで操作）
- **本番Notion DBを無確認で大量書き込みする**
- **GitHubにAPIキー・シークレットをコミットする**
- **日本語パスをcwdに直接渡す**

### ジョブズ（Claude.ai）がやってはいけないこと（2026-06-12追加）

- **ジョブズが直接コードを書く・ファイルを書き換える**
  → 実装は必ずCursorに投げる。jobz-commandで直接Pythonを書いて本番ファイルを上書きしない
- **GPT-4oゲート②なしで修正を本番反映する**
  → たとえ「緊急」「動作確認済み」でも、ゲート②を省略しない
- **「ジョブズが直接やった方が早い」という判断でCursorをスキップする**
  → 速度より手順の遵守を優先する"""

if old in content:
    new_content = content.replace(old, new)
    # 最終更新日も更新
    new_content = new_content.replace("最終更新: 2026-06-09", "最終更新: 2026-06-12")
    # 変更履歴に追記
    new_content = new_content.replace(
        "| 2026-06-09 | v2全面刷新。Cursor移行対応。CEO指示書v8・INFRA_SUMMARY最新版を反映。AI作業キュー・LINE bridge追加。 |",
        "| 2026-06-09 | v2全面刷新。Cursor移行対応。CEO指示書v8・INFRA_SUMMARY最新版を反映。AI作業キュー・LINE bridge追加。 |\n| 2026-06-12 | v3。ジョブズ直接実装禁止ルールを禁止事項に追加。ゲート②省略禁止を明文化。 |",
    )
    p.write_text(new_content, encoding="utf-8")
    print("CLAUDE.md 更新完了")
    print(f"サイズ: {p.stat().st_size}b")
else:
    print("ERROR: 置換対象が見つかりません")
