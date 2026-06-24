import re

with open(
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py",
    "r",
    encoding="utf-8",
    errors="replace",
) as f:
    content = f.read()
    lines = content.split("\n")

out = open("final_audit.txt", "w", encoding="utf-8")

# 1. API呼び出し全箇所
out.write("=== [1] Claude API呼び出し全箇所 ===\n")
current_func = ""
for i, line in enumerate(lines, 1):
    m = re.match(r"^def (\w+)", line)
    if m:
        current_func = m.group(1)
    if "call_claude(" in line or "anthropic.com/v1/messages" in line:
        out.write(f"  L{i} [{current_func}]: {line.strip()[:100]}\n")

# 2. max_tokens全箇所
out.write("\n=== [2] max_tokens設定一覧 ===\n")
for i, line in enumerate(lines, 1):
    if "max_tokens" in line:
        out.write(f"  L{i}: {line.strip()[:100]}\n")

# 3. run_double_check残存確認
out.write("\n=== [3] run_double_check残存確認 ===\n")
for i, line in enumerate(lines, 1):
    if "run_double_check" in line:
        out.write(f"  L{i}: {line.strip()[:100]}\n")
if not any("run_double_check" in l for l in lines if "def run_double_check" in l):
    out.write("  -> def run_double_check 関数定義なし OK\n")

# 4. webhookEventId実装確認
out.write("\n=== [4] webhookEventId重複防止 ===\n")
for i, line in enumerate(lines, 1):
    if "webhookEventId" in line or "PROCESSED_EVENT_IDS" in line:
        out.write(f"  L{i}: {line.strip()[:100]}\n")

# 5. グループチャット弾くロジック
out.write("\n=== [5] グループチャットフィルタ ===\n")
for i, line in enumerate(lines, 1):
    if "source_type" in line or "non-user" in line:
        out.write(f"  L{i}: {line.strip()[:100]}\n")

# 6. PDFサイズ制限
out.write("\n=== [6] PDFサイズ制限 ===\n")
for i, line in enumerate(lines, 1):
    if "file_size" in line or "5 * 1024" in line:
        out.write(f"  L{i}: {line.strip()[:100]}\n")

# 7. マッチング停止確認（run_reverse_matching_fullの呼び出し箇所）
out.write("\n=== [7] マッチング呼び出し箇所（停止確認）===\n")
for i, line in enumerate(lines, 1):
    if "run_reverse_matching_full(" in line or "run_matching(" in line:
        out.write(f"  L{i}: {line.strip()[:100]}\n")

# 8. 総行数・関数一覧
out.write("\n=== [8] ファイル概要 ===\n")
out.write(f"  総行数: {len(lines)}\n")
funcs = [l.strip() for l in lines if re.match(r"^def ", l)]
out.write(f"  関数数: {len(funcs)}\n")
for f in funcs:
    out.write(f"    {f[:80]}\n")

# 9. classify_message のmax_tokens確認
out.write("\n=== [9] classify_message詳細 ===\n")
in_classify = False
for i, line in enumerate(lines, 1):
    if "def classify_message" in line:
        in_classify = True
    if in_classify:
        out.write(f"  L{i}: {line.rstrip()[:100]}\n")
        if i > 1 and line.strip() == "" and in_classify:
            pass
        if "return" in line and in_classify and i > 10:
            break

out.write("\nAUDIT COMPLETE\n")
out.close()
print("DONE")
