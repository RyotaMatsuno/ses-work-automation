dockerfile_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\Dockerfile"

with open(dockerfile_path, "r", encoding="utf-8") as f:
    content = f.read()

print("Current Dockerfile:")
print(content)

# COPY matching_logic.py . の後に line_query.py を追加
old = "COPY matching_logic.py ."
new = "COPY matching_logic.py .\nCOPY line_query.py ."

if old in content:
    content = content.replace(old, new)
    with open(dockerfile_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("\nDockerfile updated:")
    print(content)
else:
    print("ERROR: marker not found")
