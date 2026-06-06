import os, sys

# line_query.py の先頭に日本語プロパティ定数ブロックを挿入
# これにより write_and_run の cp932 化けを完全に回避する

fpath = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py'
with open(fpath, 'rb') as f:
    raw = f.read()

# 正しいプロパティ名をbytesとして定義
props = {
    'PROP_INI':     bytes.fromhex('e382a4e3838be382b7e383a3e383ab'),  # イニシャル
    'PROP_NAME':    bytes.fromhex('e5908de5898d'),                    # 名前
    'PROP_STA':     bytes.fromhex('e69c80e5af84e3828ae9a785'),        # 最寄り駅
    'PROP_MEMO':    bytes.fromhex('e58299e88083efbc884c494e45e383a1e383a2efbc89'),  # 備考（LINEメモ）
    'PROP_SKILL':   bytes.fromhex('e382b9e382ade383ab'),              # スキル
    'PROP_RATE':    bytes.fromhex('e58d98e4bea1efbc88e4b887e58686efbc89'),  # 単価（万円）
    'PROP_STATUS':  bytes.fromhex('e382b9e38386e383bce382bfe382b9'),  # ステータス
    'PROP_REQSK':   bytes.fromhex('e5bf85e8a681e382b9e382ade383ab'),  # 必要スキル
    'PROP_OPTSK':   bytes.fromhex('e5b09ae58fafe382b9e382ade383ab'),  # 尚可スキル
    'PROP_ASSIGNEE':bytes.fromhex('e68b85e5bd93e88085'),              # 担当者
    'PROP_PJNAME':  bytes.fromhex('e6a188e4bbb6e5908d'),              # 案件名
    'PROP_PJDETAIL':bytes.fromhex('e6a188e4bbb6e8a9b3e7b4b0'),       # 案件詳細
    'PROP_REMOTE':  bytes.fromhex('e383aae383a2e383bce38388'),        # リモート
    'PROP_LOCATION':bytes.fromhex('e58ba4e58b99e59cb0'),              # 勤務地
    'PROP_PERIOD':  bytes.fromhex('e69c9fe99693'),                    # 期間
    'PROP_INTERVIEW':bytes.fromhex('e99da2e8ab87e5b88ce69c9b'),       # 面談希望
    'PROP_WORKON':  bytes.fromhex('e7a8bce5838de58fafe883bde697a5'), # 稼働可能日
    'PROP_WORKST':  bytes.fromhex('e7a8bce5838de78ab6e6b381'),       # 稼働状況
    'PROP_AFFIL':   bytes.fromhex('e68980e5b19ee4bc9ae7a4be'),       # 所属会社
    'VAL_RECRUITING': bytes.fromhex('e5aea1e99b86e4b8ad'),           # 募集中
}

# 定数ブロックのbytes構築
def b(s): return s.encode('ascii')

const_block = b'# === Notion property key constants (UTF-8 bytes) ===\n'
for name, val_bytes in props.items():
    const_block += b(name) + b' = bytes.fromhex("') + val_bytes.hex().encode() + b'").decode("utf-8")\n'
const_block += b'# ===================================================\n\n'

# ファイル先頭（import文の後）に挿入
# 'logger = logging.getLogger' の直後に挿入
marker = b'logger = logging.getLogger(__name__)'
idx = raw.find(marker)
if idx == -1:
    # fallback: 最初のimport行の後
    idx = raw.find(b'\n\n\n')
    if idx == -1:
        sys.stdout.buffer.write(b'ERROR: marker not found\n')
        sys.exit(1)

# markerの行末を見つける
line_end = raw.find(b'\n', idx) + 1

new_raw = raw[:line_end] + b'\n' + const_block + raw[line_end:]

with open(fpath, 'wb') as f:
    f.write(new_raw)

sys.stdout.buffer.write(f'Written {len(new_raw)} bytes\n'.encode('utf-8'))
sys.stdout.buffer.write(b'Constants added:\n')
for name, val_bytes in props.items():
    sys.stdout.buffer.write(f'  {name} = {val_bytes.decode("utf-8")}\n'.encode('utf-8'))
