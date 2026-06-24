import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base_dir = os.path.dirname(os.path.abspath(__file__))
files = [f"R{i:02d}" for i in range(1, 16)]

# Find actual filenames
actual_files = []
for f in sorted(os.listdir(base_dir)):
    if f.endswith(".md") and f.startswith("R") and f != "ALL_RESULTS.md":
        actual_files.append(f)

print(f"Found {len(actual_files)} files to merge:")
for f in actual_files:
    print(f"  {f}")

output_path = os.path.join(base_dir, "ALL_RESULTS.md")
with open(output_path, "w", encoding="utf-8") as out:
    for i, fname in enumerate(actual_files):
        fpath = os.path.join(base_dir, fname)
        with open(fpath, "r", encoding="utf-8") as inp:
            content = inp.read()

        if i > 0:
            out.write("\n\n")

        out.write(f"---\n{fname}\n---\n\n")
        out.write(content)

print(f"\nMerged {len(actual_files)} files -> {output_path}")
print(f"Output size: {os.path.getsize(output_path):,} bytes")
