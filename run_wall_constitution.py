# -*- coding: utf-8 -*-
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES_WORK = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

problems = [
    {
        "id": "Q1_prompt_design",
        "problem": (
            "Claude（ジョブズ）のチャット間記憶なし・ルール崩壊を防ぐための最適なプロンプト設計を教えてほしい。"
            "現状の構成案：【毎回必読】ジョブズ行動憲法.md（30行）【詰まったら読む】ハマりパターン辞書.md【参照用】CEO指示書v10.md。"
            "論点：①チャットをまたぐ記憶補完の仕組み（PJファイル・userMemory活用）"
            "②毎チャット確実に読ませるファイル構成（行動憲法30行 vs 詳細ファイル分離）"
            "③ハマりパターン辞書の最適な構造（Notion/jobz/freee/Cursor別）"
            "④引き継ぎプロトコルの改善余地。この3ファイル構成への改善提案をください。"
        ),
    },
    {
        "id": "Q2_constitution_30lines",
        "problem": (
            "AI経営参謀（Claude）の行動憲法を30行に収めるとき何を入れるべきか優先順位をつけてほしい。"
            "候補カテゴリ：①行動ルール（禁止事項・自走条件・送信確認）"
            "②事業コンテキスト（契約先TERRA粗利80%/FT68%/稼働者15名/ID類）"
            "③技術制約（jobz-command/Notion REST/freeeエンドポイント）"
            "④エスカレーション条件（2回失敗→壁打ち→松野確認）"
            "⑤モデル選択ルール（Sonnet通常/Opus月5-10回）。"
            "30行に収めるなら何を削るか・何を別ファイルに出すかの観点で意見をください。"
        ),
    },
]

for p in problems:
    print(f"\n{'=' * 60}")
    print(f"【{p['id']}】")
    print("=" * 60)
    r = subprocess.run(
        [sys.executable, "wall_hitting.py", "--problem", p["problem"]],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=SES_WORK,
        timeout=120,
    )
    print(r.stdout)
    if r.returncode != 0 and r.stderr:
        print("ERR:", r.stderr[:200])
