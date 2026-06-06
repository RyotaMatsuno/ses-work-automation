
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
tmp = [
    "check_gpt_ready.py","patch_structurer_1.py","patch_structurer_2.py",
    "patch_config_cg.py","check_syntax.py","check_indent.py","fix_indent.py",
    "add_call_openai.py","check_openai_pos.py","check_def_pos.py",
    "insert_call_openai.py","test_gpt.py","test_gpt2.py","test_gpt_final.py",
    "check_model_usage.py","check_mv3_log.py","check_mv3_cg.py",
    "check_notion_query.py","check_notion_props.py","check_eng_query.py",
    "fix_notion_filter.py","fix_eng_filter.py","check_task_status.py",
    "fix_wd_bats.py","test_mv3.py","test_mv3_final.py","test_mv3_complete.py",
    "fix_structurer_path.py","cost_check.py","cost_check2.py",
    "check_costguard_class.py","check_import.py","check_mv3_cg.py",
    "cleanup_tmp.py","check_wg.py","final_verify2.py","check_funcs.py",
    "check_def_pos.py","check_openai_pos.py",
]
deleted = sum(1 for f in tmp if (base/f).exists() and (base/f).unlink() or True if (base/f).exists() else False)
# unlink returns None、別方式で
count = 0
for f in tmp:
    p = base / f
    if p.exists():
        p.unlink()
        count += 1
print(f"削除: {count}件")
