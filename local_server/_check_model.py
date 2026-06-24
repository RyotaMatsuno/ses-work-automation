import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import re

with open(r"mail_pipeline\mail_pipeline.py", "r", encoding="utf-8", errors="replace") as f:
    content = f.read()

# Find model references
patterns = [
    r'model\s*=\s*["\'][^"\']+["\']',
    r"anthropic",
    r"openai",
    r"gpt-[\w.-]+",
    r"claude-[\w.-]+",
]
print("=== Model references ===")
for p in patterns:
    matches = re.findall(p, content, re.IGNORECASE)
    if matches:
        for m in set(matches):
            print(f"  {m}")

# Check import statements
imports = [
    l.strip()
    for l in content.split("\n")
    if "import" in l.lower() and ("anthropic" in l.lower() or "openai" in l.lower())
]
print("\n=== Import statements ===")
for i in imports:
    print(f"  {i}")

# Check API base URLs
urls = re.findall(r'https?://api\.[a-z]+\.com[^\s"\']*', content)
print("\n=== API URLs ===")
for u in set(urls):
    print(f"  {u}")
