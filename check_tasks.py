import subprocess, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

r = subprocess.run(
    ["schtasks", "/query", "/fo", "LIST", "/v"],
    capture_output=True
)
text = r.stdout.decode("cp932", errors="replace")

# 関連タスクだけ抽出
keywords = ["matching", "pipeline", "notify", "mail", "jobz", "tunnel"]
blocks = text.split("\n\n")
for block in blocks:
    bl = block.lower()
    if any(k in bl for k in keywords):
        print(block)
        print("---")
