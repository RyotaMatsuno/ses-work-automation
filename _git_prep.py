import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Add missing exclusions to .gitignore
additions = """
# State files (do not sync)
*.sqlite3
cost_guard_state.json
*.db

# Large data files
*.jsonl
match_results.jsonl
cost_log.jsonl
structured.jsonl
phase0_results.jsonl

# Virtual environments
.venv/
venv/

# Archive/temp
_archive/
_archive_tmp/
_tmp_*
_deep_*
_gpt_*
_reverify*
_save_*
_fix_*

# IDE
.idea/
.vscode/
*.swp

# OS
Thumbs.db
.DS_Store
desktop.ini

# Node
node_modules/

# Generated
*.egg-info/
dist/
build/
"""

with open('.gitignore', 'a', encoding='utf-8') as f:
    f.write(additions)

print("[OK] .gitignore updated with additional exclusions")

# Check git remote
import subprocess
r = subprocess.run(['git', 'remote', '-v'], capture_output=True, timeout=10, text=True)
print(f"\nGit remotes:\n{r.stdout}")

# Check what would be committed now
r2 = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, timeout=30, text=True)
changes = [l for l in r2.stdout.strip().split('\n') if l.strip()]
print(f"Files to commit after .gitignore update: {len(changes)}")

# Check for any secrets in tracked files
r3 = subprocess.run(['git', 'ls-files'], capture_output=True, timeout=15, text=True)
tracked = r3.stdout.strip().split('\n')
dangerous = [f for f in tracked if any(k in f.lower() for k in ['.env', 'token', 'credential', 'secret', 'password'])]
if dangerous:
    print(f"\n⚠️ Potentially dangerous tracked files:")
    for d in dangerous:
        print(f"  {d}")
else:
    print(f"\n✅ No secret files in tracked files")
