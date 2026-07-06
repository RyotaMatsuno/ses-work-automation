import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import os

SES = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

# Search for 選考中 in all Python files
results = []
for root, dirs, files in os.walk(SES):
    # Skip .git, node_modules, __pycache__
    dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '__pycache__', '.venv', 'venv']]
    for f in files:
        if f.endswith('.py'):
            fpath = os.path.join(root, f)
            try:
                with open(fpath, 'r', encoding='utf-8', errors='replace') as fh:
                    lines = fh.readlines()
                for i, line in enumerate(lines):
                    if '選考中' in line:
                        rel = os.path.relpath(fpath, SES)
                        results.append((rel, i+1, line.strip()))
            except:
                pass

print(f"=== '選考中' found in {len(results)} lines ===\n")
for rel, ln, line in results:
    print(f"  {rel}:{ln}")
    print(f"    {line[:120]}")
    print()
