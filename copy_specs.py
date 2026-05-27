import os, shutil

src = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_notify_fix'
dst_base = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work'

# SPEC.md, TASKS.md, CLAUDE.md をses_work直下にコピー
for fname in ['SPEC.md', 'TASKS.md', 'CLAUDE.md']:
    src_path = os.path.join(src, fname)
    dst_path = os.path.join(dst_base, f'PFIX_{fname}')
    shutil.copy2(src_path, dst_path)
    print(f'copied: {dst_path}')
