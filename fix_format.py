import io
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# format_project_result の業務内容を短くする修正
# 現状: 案件詳細をそのまま表示（メール本文300文字）
# 修正: 案件名・必須スキル・単価・勤務地・期間・粗利のみ（コンパクト版）

paths = [
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py",
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py",
]

for path in paths:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    fname = "/".join(path.split("\\")[-2:])

    # format_project_result の案件表示部分を短縮
    OLD_FORMAT = """        lines.extend(


            [


                \"\",


                \"━━━━━━━━━━━━\",


                f\"{_num_label(index)}{_text_prop(project, \'案件名\')}\",


                \"━━━━━━━━━━━━\",


                f\"業務内容  : {_text_prop(project, \'案件詳細\')}\",


                f\"必要スキル: {_join(_multi_select_prop(project, \'必要スキル\'))}\",


                f\"尚可スキル: {_join(_multi_select_prop(project, \'尚可スキル\'))}\",


                f\"勤務地    : {_text_prop(project, \'勤務地\')}（リモート: {_select_prop(project, \'リモート\')}）\",


                f\"期間      : {_text_prop(project, \'期間\')}\",


                f\"面談      : {_format_number(_number_prop(project, \'面談希望\'))}回\",


                f\"提示単価  : {_format_number(_number_prop(project, \'単価（万円）\'))}万円\",


                f\"粗利      : {_format_number(item[\'gross_profit\'])}万円\",


                f\"担当      : {_select_prop(project, \'担当者\')}\",


                f\"鮮度      : 最終更新{business_days_since(project.get(\'last_edited_time\'))}日前\",


            ]


        )"""

    NEW_FORMAT = """        _pj_name = _text_prop(project, '案件名')
        _req_sk = _join(_multi_select_prop(project, '必要スキル'))
        _opt_sk = _join(_multi_select_prop(project, '尚可スキル'))
        _loc = _text_prop(project, '勤務地')
        _remote = _select_prop(project, 'リモート')
        _period = _text_prop(project, '期間')
        _budget = _number_prop(project, '単価（万円）')
        _gross = item['gross_profit']
        _age = business_days_since(project.get('last_edited_time'))
        lines.extend(
            [
                "",
                f"{_num_label(index)} {_pj_name}",
                f"  必須: {_req_sk or '未設定'}" + (f" / 尚可: {_opt_sk}" if _opt_sk else ""),
                f"  単価: {_format_number(_budget)}万 / 粗利: {_format_number(_gross)}万",
                f"  {_loc}（{_remote}）{' / ' + _period if _period else ''} [{_age}日前]",
            ]
        )"""

    if OLD_FORMAT in content:
        content = content.replace(OLD_FORMAT, NEW_FORMAT, 1)
        print(f"✅ {fname}: 案件表示コンパクト化 OK")
    else:
        print(f"❌ {fname}: パターン不一致")
        idx = content.find("format_project_result")
        if idx >= 0:
            # 実際のextend部分を探す
            idx2 = content.find("lines.extend", idx)
            print(f"  lines.extend位置: {idx2}")
            if idx2 >= 0:
                print(f"  実際: {repr(content[idx2 : idx2 + 300])}")

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    r = subprocess.run(["python", "-m", "py_compile", path], capture_output=True, text=True)
    if r.returncode == 0:
        print(f"✅ {fname}: 構文OK")
    else:
        print(f"❌ {fname}: {r.stderr}")
    print()
