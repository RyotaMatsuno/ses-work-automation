path = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# normalize_price関数とその呼び出しを追加
func = '''
def normalize_price(price):
    """AIが万円単位を誤って円単位で返した場合に正規化する。
    100以上かつ100の倍数っぽい大きな値は万円換算とみなして割る。
    合理的な万円範囲: 30〜200万円
    """
    if price is None or price == 0:
        return price
    # 1000以上なら円単位と判断して万円に変換
    if price >= 1000:
        price = round(price / 10000)
    return price

'''

# classify_message関数の前に挿入
insert_before = 'def classify_message(text):'
content = content.replace(insert_before, func + insert_before, 1)

# register_engineer内でnormalize_priceを使う
old_eng = '    if info.get("price"): props["\\u5358\\u4fa1\\uff08\\u4e07\\u5186\\uff09"] = {"number": info["price"]}\n    if info.get("experience_years")'
new_eng = '    price_val = normalize_price(info.get("price", 0))\n    if price_val: props["\\u5358\\u4fa1\\uff08\\u4e07\\u5186\\uff09"] = {"number": price_val}\n    if info.get("experience_years")'
content = content.replace(old_eng, new_eng, 1)

# register_project内でnormalize_priceを使う
old_prj = '    if info.get("price"): props["\\u5358\\u4fa1\\uff08\\u4e07\\u5186\\uff09"] = {"number": info["price"]}\n    if info.get("location")'
new_prj = '    price_val = normalize_price(info.get("price", 0))\n    if price_val: props["\\u5358\\u4fa1\\uff08\\u4e07\\u5186\\uff09"] = {"number": price_val}\n    if info.get("location")'
content = content.replace(old_prj, new_prj, 1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("done")
