import sys

sys.stdout.reconfigure(encoding="utf-8")
with open("matching_v2/matching_v2.py", encoding="utf-8") as f:
    lines = f.readlines()
# main()のprojects取得直後の行番号を特定
for i, line in enumerate(lines):
    if (
        "extract_project" in line
        or "extract_engineer" in line
        or "for page in query_db" in line
        or "load_sample_data" in line
        or "validate_env" in line
    ):
        print(f"{i + 1}: {repr(line.rstrip())}")
