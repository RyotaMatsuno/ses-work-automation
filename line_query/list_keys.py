import os

fpath = os.path.join(os.path.dirname(__file__), "line_query.py")
with open(fpath, "rb") as f:
    raw = f.read()
text = raw.decode("utf-8")

# engineer_query 内で使われているプロパティキーを全部洗い出す
# _text_prop / _select_prop / _multi_select_prop / _number_prop の引数を列挙
import re

calls = re.findall(r'_(?:text|select|multi_select|number|date)_prop\([\w]+,\s*["\']([^"\']+)["\']', text)
print("All prop keys found in file:")
for c in sorted(set(calls)):
    print(f"  {repr(c)}  hex={c.encode('utf-8').hex()}")
