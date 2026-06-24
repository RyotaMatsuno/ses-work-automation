# Codexが生成したline_query.pyをcp932で読んでUTF-8で保存する
# cp932変換不能文字は正しいUTF-8キーで置き換える

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py"
bak_path = path + ".bak_orig"

with open(path, "rb") as f:
    raw = f.read()

# バックアップ
with open(bak_path, "wb") as f:
    f.write(raw)

# cp932でデコード（置換文字使用）
content = raw.decode("cp932", errors="replace")

# 置換文字(\ufffd)が混入しているキーを正しいUTF-8に修正
replacements = {
    # 文字化けしたNotionプロパティ名 → 正しい日本語
    # cp932デコード後の形で指定
    '_text_prop(engineer, "最寄り\ufffd\ufffd")': '_text_prop(engineer, "最寄り駅")',
    '_text_prop(engineer, "備考（LINE\ufffdメモ）")': '_text_prop(engineer, "備考（LINEメモ）")',
}

# まず実際にどんな文字化けが起きているか確認
import re

# _text_propの引数を全部抽出
all_keys = re.findall(r'_text_prop\([^,]+,\s*"([^"]*)"', content)
print("Keys found:")
for k in all_keys:
    print(f"  {repr(k)}")
