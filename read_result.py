import json

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\result.json"
with open(path, encoding="utf-8") as f:
    data = json.load(f)
print(f"総マッチ件数: {len(data)}件")
ok = [d for d in data if not d["needs_check"]]
ng = [d for d in data if d["needs_check"]]
print(f"✅提案推奨: {len(ok)}件 / ⚠️要確認: {len(ng)}件\n")
print("=== 提案推奨（スコア1.0）===")
for item in [d for d in ok if d["score"] == 1.0][:10]:
    print(f"  {item['engineer_name']} × {item['project_name'][:30]}")
print("\n=== 要確認トップ5 ===")
for item in sorted(ng, key=lambda x: x["score"], reverse=True)[:5]:
    print(f"  スコア{item['score']:.2f} {item['engineer_name']} × {item['project_name'][:30]}")
