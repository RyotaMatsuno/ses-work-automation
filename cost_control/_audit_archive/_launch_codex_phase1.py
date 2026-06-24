import datetime
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WD = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
CODEX = r"C:\Users\ma_py\AppData\Roaming\npm\codex.cmd"
LOG = os.path.join(WD, "cost_control", "codex_phase1.log")
os.makedirs(os.path.join(WD, "cost_control"), exist_ok=True)

if not os.path.exists(CODEX):
    with open(LOG, "w", encoding="utf-8") as f:
        f.write(f"ERROR: codex not found at {CODEX}\n")
    print("CODEX NOT FOUND", CODEX)
    sys.exit(0)

prompt = (
    "cost_control/SPEC.md と cost_control/TASKS.md と cost_control/CLAUDE.md を読んでください。"
    "Phase 1（C1 Sonnet合理化 / C2 モデル名env一元化 / C3 cost_guard横展開）のみを TASKS.md の順に実装してください。"
    "厳守事項: (1)送信系ロジック(メール送信・LINE push/reply・freee送信・成約フロー送信部)には一切触れない。"
    "(2)モデル名のハードコードを新規追加しない。env(TEXT_MODEL/VISION_MODEL/STRUCTURER_MODEL/MATCH_MODEL)経由にする。"
    "(3)skill_reader.pyのextract_skills_from_textとoutlook_to_notion.pyの分類はSonnet→Haikuに変更。"
    "(4)skill_judge.pyの_select_fallback_modelのSonnetフォールバックを廃止しHaikuピン留めかハードエラーに。"
    "(5)extract_skills_from_imageはVISION_MODEL参照(既定はSonnet維持)。"
    "(6)common/ledger.pyのガードをmail_pipeline/skill_reader/outlook_to_notionへ適用(DAILY $1, MONTHLY $6, env可変)。"
    "(7)各変更後にpy_compileで構文確認し結果をtxtに書く。stderr直読み禁止。"
    "(8)Phase2/Phase3には着手しない。完了したタスクのみTASKS.mdのチェックボックスをチェック。"
)
f = open(LOG, "w", encoding="utf-8")
f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} codex launch (Phase1)\n")
f.flush()
subprocess.Popen(
    [CODEX, "exec", prompt, "-C", WD, "--dangerously-bypass-approvals-and-sandbox"],
    stdout=f,
    stderr=subprocess.STDOUT,
    creationflags=0x08000000,
    cwd=WD,
)
print("codex Phase1 launched (background). log:", LOG)
