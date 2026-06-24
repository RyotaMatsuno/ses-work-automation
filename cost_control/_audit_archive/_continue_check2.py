import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
out = []


def w(*a):
    out.append(" ".join(str(x) for x in a))


# 1. SES_MailPipeline status + next run
w("=== SES_MailPipeline task ===")
q = subprocess.run(
    ["schtasks", "/query", "/tn", "SES_MailPipeline", "/fo", "list"],
    capture_output=True,
    text=True,
    encoding="cp932",
    errors="replace",
)
for line in (q.stdout or q.stderr).splitlines():
    if any(k in line for k in ["状態", "次回", "前回", "Status", "Next", "Last", "タスク名", "TaskName"]):
        w("  " + line.strip()[:110])

# 2. last 起動/v5.1 timestamp in pipeline.log (scan full file, memory-light)
w("\n=== pipeline.log last startup marker ===")
mp = os.path.join(BASE, "mail_pipeline", "pipeline.log")
last_start = None
last_excl = None
last_cls = None
n_excl_total = 0
if os.path.exists(mp):
    with open(mp, encoding="utf-8", errors="replace") as f:
        for line in f:
            if "起動" in line or "v5.1" in line:
                last_start = line.strip()
            if "配信除外" in line:
                last_excl = line.strip()
                n_excl_total += 1
            if "分類対象" in line:
                last_cls = line.strip()
    w(f"  最終起動行: {last_start[:120] if last_start else '(なし=新コード未稼働の可能性)'}")
    w(f"  配信除外ログ累計: {n_excl_total} / 最終: {last_excl[:110] if last_excl else '(なし)'}")
    w(f"  最終分類対象行: {last_cls[:110] if last_cls else '(なし)'}")

# 3. is_broadcast synthetic test (guarded import)
w("\n=== is_broadcast 合成テスト ===")
try:
    sys.path.insert(0, os.path.join(BASE, "mail_pipeline"))
    import importlib

    mpmod = importlib.import_module("mail_pipeline")
    isb = getattr(mpmod, "is_broadcast", None)
    if isb is None:
        w("  is_broadcast 取得不可")
    else:
        cases = [
            (
                "List-Unsubscribeあり",
                {
                    "sender": "news@bulk.example.com",
                    "headers": {"list-unsubscribe": "<mailto:u@x>"},
                    "body": "案件のお知らせ",
                    "to": "a@x",
                },
                True,
            ),
            (
                "フッタに配信停止",
                {
                    "sender": "info@example.com",
                    "headers": {},
                    "body": "案件詳細...\n\n配信停止はこちら https://x/unsub",
                    "to": "a@x",
                },
                True,
            ),
            (
                "通常の個別案件",
                {
                    "sender": "tanaka@bp-partner.co.jp",
                    "headers": {},
                    "body": "下記案件いかがでしょうか。Java/AWS、70万、即日",
                    "to": "sessales@terra-ltd.co.jp",
                },
                False,
            ),
        ]
        for name, msg, exp in cases:
            try:
                got = isb(msg)
                mark = "OK" if got == exp else "★NG"
                w(f"  [{mark}] {name}: 期待={exp} 実際={got}")
            except Exception as e:
                w(f"  [ERR] {name}: {e}")
except Exception as e:
    w(f"  import失敗(別途ログ検証で代替): {type(e).__name__}: {str(e)[:120]}")

with open(os.path.join(BASE, "_continue_check2.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("DONE")
