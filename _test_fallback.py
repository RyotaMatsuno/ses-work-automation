import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, "mail_pipeline")

# _keyword_classify を単体テスト
import importlib.util

spec = importlib.util.spec_from_file_location("mp", "mail_pipeline/mail_pipeline.py")
# 直接関数定義だけ読み込む
with open("mail_pipeline/mail_pipeline.py", encoding="utf-8") as f:
    src = f.read()

# _keyword_classify だけ抽出して実行
import re as _re

exec_globals = {"re": _re, "log": print}
m = _re.search(r"def _keyword_classify.*?(?=\ndef )", src, _re.DOTALL)
if m:
    exec(m.group(), exec_globals)
    fn = exec_globals["_keyword_classify"]

    tests = [
        ("【C-TOS案件情報】（7月〜／勝どき）生保会社向けシステムのPMO募集 面談1回", ""),
        ("【ゼロスピリッツ】案件情報をお送りします（2026年6月12日版）", "案件 Java 45万"),
        ("【SBT◆技術者】Javaエンジニア ◆ 要件定義〜可 ◆ 78万 ◆ 7月〜", ""),
        ("【ボードルア】7月～9月分御見積書のご送付", ""),
        ("※最注力案件　8件　【アイエンター鈴木】", "案件 募集 稼働 7月"),
    ]
    print("=== キーワードフォールバック テスト ===")
    for subj, body in tests:
        result = fn(subj, body)
        r = result["type"] if result else "None(→other)"
        print(f"  [{r}] {subj[:50]}")
