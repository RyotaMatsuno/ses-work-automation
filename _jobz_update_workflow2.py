import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = Path(os.getcwd())
p = SES / "project_files" / "cursor_workflow_rules.md"
content = p.read_text(encoding="utf-8")

addition = """
## ジョブズ直接実装禁止ルール（2026-06-12確定）

### 背景
2026-06-12、ジョブズが「緊急対応」として flag_auto_updater と matching_v3 の
logging修正を jobz-command 経由で直接実施し、かつゲート②も省略した。
動作確認後に事後ゲートを通したが、手順違反であった。

### ルール（絶対遵守）

| 状況 | 正しい対応 |
|---|---|
| バグ発見・修正が必要 | Cursor作業指示書を生成 → pending_tasks/ に保存 → Cursorが実装 |
| 「1行だけ直せば済む」 | それでもCursor指示書を出す。例外なし |
| 「緊急で今すぐ直さないと」 | Cursor指示書を出してCursorを開くよう松野に依頼する |
| ジョブズがjobz-commandで本番ファイルを直接書き換える | **禁止** |

### ゲート②省略禁止

- 実装完了後は必ずGPT-4oゲート②を通す
- 「動作確認済みだから大丈夫」はゲート②省略の理由にならない
- ジョブズが直接実装した場合も例外なくゲート②を通す（今回の教訓）

### チェックリスト（Cursor作業完了時）
- [ ] ゲート② (GPT-4o) でコードレビューを実施したか
- [ ] GO判定を確認したか
- [ ] pending_tasks/ から done_tasks/ にファイルを移動したか
"""

new_content = content.rstrip() + "\n" + addition
p.write_text(new_content, encoding="utf-8")
print(f"cursor_workflow_rules.md 更新完了 ({p.stat().st_size}b)")
