from pathlib import Path

BASE = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")

# 追加ファイル
extra = [
    "mail_pipeline/mail_pipeline.py",
    "mail_pipeline/mail_pipeline_test1.py",
]

out_path = BASE / "code_export.md"
with open(out_path, "a", encoding="utf-8") as f:
    for rel in extra:
        p = BASE / rel
        if p.exists():
            ext = p.suffix.lstrip(".")
            f.write(f"## {rel}\n\n```{ext}\n")
            f.write(p.read_text(encoding="utf-8", errors="replace"))
            f.write("\n```\n\n")
            print(f"追加: {rel}")
        else:
            print(f"未発見: {rel}")

print("追記完了")
