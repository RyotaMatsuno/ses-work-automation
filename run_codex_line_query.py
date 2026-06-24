import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

CODEX = r"C:\Users\ma_py\AppData\Roaming\npm\codex.cmd"
CWD = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"
LOG = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\codex_detail_run.log"

prompt = (
    "SPEC_project_detail.md を読んで line_query.py を修正してください。"
    "修正前に line_query.py.bak_0602 を作成すること。"
    "修正内容: "
    "1) classify_queryのイニシャル判定を4文字以内に厳密化（Oracleなど誤判定修正）"
    "2) _LAST_ENG_RESULTS/_LAST_PROJ_RESULTS/_LAST_QUERY_TYPE の3変数追加"
    "3) project_queryでエンジニアキャッシュを保存"
    "4) detail_queryをエンジニア側・案件側両対応に拡張"
    "5) format_engineer_detail関数を新規作成（人員情報原文全文+DriveリンクURL含む）"
    "全修正後に python -m py_compile line_query.py で構文チェックを実行すること。"
)

with open(LOG, "w", encoding="utf-8") as lf:
    proc = subprocess.Popen(
        [CODEX, "exec", prompt, "--dangerously-bypass-approvals-and-sandbox", "-C", CWD], stdout=lf, stderr=lf, cwd=CWD
    )

print(f"Codex起動 PID: {proc.pid}", flush=True)
print(f"ログ: {LOG}", flush=True)
