# -*- coding: utf-8 -*-
import io
import shutil
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

p3 = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\notify_line.py"
shutil.copy2(p3, p3 + ".bak_pfix")

content = open(p3, encoding="utf-8").read()

# ---- Fix A: get_page_info() project に raw_body 追加 ----
old_proj = """            "period": get_text_property(props, "期間"),
            "url": "",  # main()でresult.jsonから上書きセット
        }"""
new_proj = """            "period": get_text_property(props, "期間"),
            "raw_body": get_first_text_property(props, ["案件詳細", "備考（LINEメモ）"]),
            "url": "",  # main()でresult.jsonから上書きセット
        }"""
if old_proj in content:
    content = content.replace(old_proj, new_proj, 1)
    print("OK: get_page_info project raw_body追加")
else:
    print("NG: project raw_body パターン見つからず")

# ---- Fix B: get_page_info() engineer に raw_body 追加 ----
old_eng = """            "affiliation": get_text_property(props, "所属会社名"),
            "url": "",  # main()でresult.jsonから上書きセット
        }

    raise ValueError"""
new_eng = """            "affiliation": get_text_property(props, "所属会社名"),
            "raw_body": get_text_property(props, "備考（LINEメモ）"),
            "url": "",  # main()でresult.jsonから上書きセット
        }

    raise ValueError"""
if old_eng in content:
    content = content.replace(old_eng, new_eng, 1)
    print("OK: get_page_info engineer raw_body追加")
else:
    print("NG: engineer raw_body パターン見つからず")

# ---- Fix C: empty_page_info() project に raw_body 追加 ----
old_ep = """            "period": "",
            "url": "",
        }"""
new_ep = """            "period": "",
            "raw_body": "",
            "url": "",
        }"""
if old_ep in content:
    content = content.replace(old_ep, new_ep, 1)
    print("OK: empty_page_info project raw_body追加")
else:
    print("NG: empty_page_info project raw_body パターン見つからず")

# ---- Fix D: empty_page_info() engineer に raw_body 追加 ----
old_ee = """        "affiliation": "",
        "url": "",
    }"""
new_ee = """        "affiliation": "",
        "raw_body": "",
        "url": "",
    }"""
if old_ee in content:
    content = content.replace(old_ee, new_ee, 1)
    print("OK: empty_page_info engineer raw_body追加")
else:
    print("NG: empty_page_info engineer raw_body パターン見つからず")

open(p3, "w", encoding="utf-8").write(content)
print("notify_line.py 書き込み完了")
