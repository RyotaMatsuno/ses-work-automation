# -*- coding: utf-8 -*-
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# matching_v3のタスクスケジューラを確認
r = subprocess.run(
    ["schtasks", "/query", "/tn", "SES_MatchingV3", "/fo", "LIST", "/v"], capture_output=True, timeout=10
)
print(r.stdout.decode("cp932", errors="replace")[:1000])
