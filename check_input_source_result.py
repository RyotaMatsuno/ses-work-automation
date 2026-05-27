import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
with open('codex_input_source.log','r',encoding='utf-8',errors='replace') as f:
    content = f.read()
lines = content.splitlines()
# add_input_source_fields.pyの実行後の出力を探す
for i, line in enumerate(lines):
    if 'add_input_source_fields' in line and i > 14000:
        for j in range(i, min(i+30, len(lines))):
            print(f"L{j}: {lines[j][:150]}")
        print("---")
