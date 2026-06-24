import datetime
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WD = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
CODEX = r"C:\Users\ma_py\AppData\Roaming\npm\codex.cmd"
LOG = os.path.join(WD, "cost_control", "codex_phase3a.log")
prompt = (
    "cost_control/AUDIT_FIXES.md と cost_control/CLAUDE.md を読んで、AUDIT_FIXES.md の F2/F3/F6/F8/F10 を順に実装してください。"
    "除外項目(F7/F12/F4)には絶対に着手しないこと。送信系(メール送信・LINE push/reply・freee送信・成約フロー送信)には一切触れない。"
    "モデル名の新規ハードコード禁止(common/model_config.pyのTEXT_MODEL等を使う)。common/ledger.pyのcan_spend/recordを使う。"
    "各ファイル変更後にpy_compileで構文確認し、結果を cost_control_phase3_compile.txt に追記(stderr直読み禁止)。"
    "明示された箇所以外の挙動は変えない。最後に変更ファイル一覧と各Fの実装要約を出力。"
)
f = open(LOG, "w", encoding="utf-8")
f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} codex Phase3a launch\n")
f.flush()
subprocess.Popen(
    [CODEX, "exec", prompt, "-C", WD, "--dangerously-bypass-approvals-and-sandbox"],
    stdout=f,
    stderr=subprocess.STDOUT,
    creationflags=0x08000000,
    cwd=WD,
)
print("codex Phase3a launched (background). log:", LOG)
