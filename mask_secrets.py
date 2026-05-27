
from pathlib import Path
import re

p = Path(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\code_export_tmp.md')
text = p.read_text(encoding='cp932', errors='replace')

replacements = [
    # freee client_secret 実値
    (r'CLIENT_SECRET\s*=\s*"[A-Za-z0-9_\-]+"',
     'CLIENT_SECRET = "***MASKED***"'),
    # Matsuno LINE user_id フォールバック実値
    (r"(MATSUNO_USER_ID\s*=.*?or\s*')[A-Za-z0-9]+(')",
     r'\1***MASKED***\2'),
    # Okamoto LINE user_id フォールバック実値
    (r"(OKAMOTO_USER_ID\s*=.*?or\s*')[A-Za-z0-9]+(')",
     r'\1***MASKED***\2'),
]

count = 0
for pattern, replacement in replacements:
    new_text, n = re.subn(pattern, replacement, text)
    if n:
        print(f"マスク済み ({n}件): {pattern[:50]}")
        count += n
        text = new_text

p.write_text(text, encoding='utf-8')
print(f"\n合計 {count} 箇所マスク完了 → code_export_tmp.md 更新")
