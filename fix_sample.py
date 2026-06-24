import json

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\test_data\sample.json"
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

# エンジニアAの単価を58万に（粗利7万確保）
data["engineers"][0]["price"] = 58
# ownerを松野に設定（粗利閾値5万適用のため）
data["engineers"][0]["owner"] = "松野"
data["projects"][0]["owner"] = "松野"

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print("sample.json updated")
