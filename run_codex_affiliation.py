import subprocess

codex_cmd = r"C:\Users\ma_py\AppData\Roaming\npm\codex.cmd"

# ① webhook_server.py 所属フィールド対応
log1 = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\codex_affiliation.log"
with open(log1, "w", encoding="utf-8") as f:
    p1 = subprocess.Popen(
        [
            codex_cmd,
            "exec",
            "SPEC_affiliation_fields.mdを読んで、webhook_server.pyのclassify_message()のsystem promptとregister_engineer()を修正してください。他の既存機能は変更しないこと。",
            "--dangerously-bypass-approvals-and-sandbox",
        ],
        cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook",
        stdout=f,
        stderr=f,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
    )
    print(f"webhook PID: {p1.pid}", flush=True)

# ② composer.py 所属フィールド対応
log2 = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\codex_composer.log"
composer_spec = """所属会社・所属担当者名を使うようにcomposer.pyを修正してください。
fetcher.pyのnormalize_engineer()に以下を追加:
  "affiliation": property_value(props, "所属会社") or "",
  "contact_name": property_value(props, "所属担当者名") or "",
  "contact_email": property_value(props, "所属メール") or "",
そしてcomposer.pyのテンプレート文字列で
「所属会社 {担当者名}様」の部分を
engineer["affiliation"] と engineer["contact_name"] で埋めるよう修正してください。
空の場合は「{所属会社名} {担当者名}様」のプレースホルダーを残す。
他の既存機能は変更しないこと。"""

with open(log2, "w", encoding="utf-8") as f:
    p2 = subprocess.Popen(
        [codex_cmd, "exec", composer_spec, "--dangerously-bypass-approvals-and-sandbox"],
        cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_v1",
        stdout=f,
        stderr=f,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
    )
    print(f"composer PID: {p2.pid}", flush=True)
