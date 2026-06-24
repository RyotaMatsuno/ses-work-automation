import os, sys

fpath = os.path.join(os.path.dirname(__file__), 'line_query.py')
with open(fpath, 'rb') as f:
    raw = f.read()

# 稼働可能日・稼働状況の実際のbytesを確認
for search_ascii in [b'e5838d', b'_PROP_INI', b'\xe7\xa8\xbc\xe5\x83\x8d']:
    idx = raw.find(b'\xe7\xa8\xbc')  # 稼
    if idx >= 0:
        chunk = raw[idx:idx+20]
        sys.stdout.buffer.write(b'Found at ' + str(idx).encode() + b': ' + chunk.hex().encode() + b'\n')
        sys.stdout.buffer.write(chunk + b'\n')
        break

# 稼働可能日 の正しいbytes (Notionから取得済み): e7a8bce5838de58fafe883bde697a5
target = bytes.fromhex('e7a8bce5838de58fafe883bde697a5')
if target in raw:
    sys.stdout.buffer.write(b'OK: kado-kanou-bi correct bytes FOUND\n')
else:
    sys.stdout.buffer.write(b'NG: kado-kanou-bi correct bytes NOT FOUND\n')

# 稼働状況 の正しいbytes: e7a8bce5838de78ab6e6b381
target2 = bytes.fromhex('e7a8bce5838de78ab6e6b381')
if target2 in raw:
    sys.stdout.buffer.write(b'OK: kado-jokyo correct bytes FOUND\n')
else:
    sys.stdout.buffer.write(b'NG: kado-jokyo correct bytes NOT FOUND\n')

# ファイル内の稼から始まるすべての文字列を検索
import re
text = raw.decode('utf-8')
matches = re.findall(r'稼\S+', text)
sys.stdout.buffer.write(b'All 稼xxx in file:\n')
for m in set(matches):
    sys.stdout.buffer.write(f'  {m!r}  {m.encode("utf-8").hex()}\n'.encode('utf-8'))
