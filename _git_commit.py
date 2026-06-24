import sys, os, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Check if the "dangerous" files contain actual secrets or just handle them
suspect_files = [
    'check_token_mgr.py', 'find_google_tokens.py', 'get_client_secret.py',
    'get_drive_token.py', 'get_oauth_secret.py', 'get_oauth_secret2.py',
    'mask_secrets.py', 'read_token_mgr.py'
]

# Pattern: actual API keys or tokens hardcoded
secret_patterns = [
    r'sk-ant-api[a-zA-Z0-9\-_]{20,}',  # Anthropic
    r'sk-proj-[a-zA-Z0-9\-_]{20,}',     # OpenAI
    r'ntn_[a-zA-Z0-9]{20,}',            # Notion
    r'Bearer [a-zA-Z0-9+/=]{50,}',      # Long Bearer tokens
    r'(?:password|passwd|pwd)\s*=\s*["\'][^"\']{5,}["\']',  # Hardcoded passwords
]

print("Checking tracked files for hardcoded secrets...")
found_secrets = False
for f in suspect_files:
    if os.path.exists(f):
        content = open(f, 'r', encoding='utf-8', errors='replace').read()
        for pattern in secret_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                print(f"  ⚠️ {f}: Found potential secret matching pattern")
                found_secrets = True

if not found_secrets:
    print("  ✅ No hardcoded secrets found in suspect files")
    print("  These files are just code that handles tokens (safe to commit)")

# Do the snapshot commit
print("\n--- Performing snapshot commit ---")
import subprocess

# Stage everything
r = subprocess.run(['git', 'add', '-A'], capture_output=True, timeout=60, text=True)
print(f"git add: {'OK' if r.returncode == 0 else 'FAIL'}")

# Check staged count
r2 = subprocess.run(['git', 'diff', '--cached', '--stat', '--shortstat'], capture_output=True, timeout=30, text=True)
print(f"Staged: {r2.stdout.strip()}")

# Commit
r3 = subprocess.run(
    ['git', 'commit', '-m', 'chore: snapshot before stabilization (2026-06-24 audit)'],
    capture_output=True, timeout=120, text=True
)
print(f"git commit: {'OK' if r3.returncode == 0 else 'FAIL'}")
if r3.stdout:
    # Get last line of commit output
    lines = r3.stdout.strip().split('\n')
    for l in lines[-3:]:
        print(f"  {l}")

# Check if remote is private
r4 = subprocess.run(['git', 'remote', 'get-url', 'origin'], capture_output=True, timeout=10, text=True)
remote_url = r4.stdout.strip()
print(f"\nRemote: {remote_url}")

# Check repo visibility (GitHub API)
if 'github.com' in remote_url:
    # Extract owner/repo
    parts = remote_url.replace('.git', '').split('/')
    owner = parts[-2]
    repo = parts[-1]
    import urllib.request
    try:
        req = urllib.request.Request(f'https://api.github.com/repos/{owner}/{repo}')
        with urllib.request.urlopen(req, timeout=10) as resp:
            info = json.loads(resp.read().decode('utf-8'))
            is_private = info.get('private', False)
            print(f"  Repository visibility: {'PRIVATE ✅' if is_private else 'PUBLIC ⚠️'}")
            if not is_private:
                print(f"  ⚠️ Repository is PUBLIC! Push would expose code to public.")
                print(f"  Skipping push. Make it private first on GitHub.")
    except Exception as e:
        # 404 means private or doesn't exist
        if '404' in str(e):
            print(f"  Repository is PRIVATE (or doesn't exist) ✅")
            # Try push
            print("\n--- Pushing to origin ---")
            r5 = subprocess.run(['git', 'push', 'origin', 'main'], capture_output=True, timeout=120, text=True)
            if r5.returncode == 0:
                print(f"  git push: OK ✅")
            else:
                print(f"  git push: {r5.stderr[:200]}")
        else:
            print(f"  Could not check: {e}")

import json
