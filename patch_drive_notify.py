path = "matching_v2/notify_line.py"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

with open(path + ".bak_drive", "w", encoding="utf-8") as f:
    f.write(src)

# build_project_message内のエンジニアraw_bodyセクションの後にDriveリンク追加
old_eng_raw = """        if eng_raw:
            lines.append("")
            lines.append(f"【元データ（{eng_name}）】")
            preview = eng_raw[:1500]
            lines.append(preview)
            if len(eng_raw) > 1500:
                lines.append(f"... (total {len(eng_raw)} chars, truncated)")"""

new_eng_raw = """        if eng_raw:
            lines.append("")
            lines.append(f"【元データ（{eng_name}）】")
            preview = eng_raw[:1500]
            lines.append(preview)
            if len(eng_raw) > 1500:
                lines.append(f"... (total {len(eng_raw)} chars, truncated)")
        drive_url = eng_info.get("drive_url", "").strip()
        if drive_url:
            lines.append("")
            lines.append(f"【添付ファイル（{eng_name}）】")
            lines.append(drive_url)"""

src = src.replace(old_eng_raw, new_eng_raw)
print("Patch 5 (notify_line Drive link):", "OK" if "添付ファイル" in src else "FAILED")

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("Saved.")
