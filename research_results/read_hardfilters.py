import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import os

# Check hard_filters.py for FilterDropStats or logging
hf_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\hard_filters.py"
with open(hf_path, 'r', encoding='utf-8') as f:
    content = f.read()

print("=== hard_filters.py ===")
print(f"Size: {len(content)} bytes")
print(content)
