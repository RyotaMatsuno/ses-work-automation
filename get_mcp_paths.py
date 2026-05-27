import json, os, sys, subprocess
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# グローバルnpmのmainエントリポイントを取得
def get_global_main(pkg_name):
    npm_root = subprocess.check_output(
        ['npm', 'root', '-g'], encoding='utf-8', errors='replace'
    ).strip()
    pkg_dir = os.path.join(npm_root, *pkg_name.split('/'))
    pkg_json = os.path.join(pkg_dir, 'package.json')
    with open(pkg_json, 'r', encoding='utf-8') as f:
        pkg = json.load(f)
    # bin > main の順で探す
    if 'bin' in pkg:
        bin_val = pkg['bin']
        if isinstance(bin_val, str):
            return os.path.join(pkg_dir, bin_val)
        elif isinstance(bin_val, dict):
            first = list(bin_val.values())[0]
            return os.path.join(pkg_dir, first)
    main = pkg.get('main', 'index.js')
    return os.path.join(pkg_dir, main)

pkgs = [
    '@modelcontextprotocol/server-memory',
    '@modelcontextprotocol/server-sequential-thinking',
    '@upstash/context7-mcp',
]
for pkg in pkgs:
    path = get_global_main(pkg)
    exists = os.path.exists(path)
    print(f"{pkg}:\n  {path}\n  exists={exists}\n")
