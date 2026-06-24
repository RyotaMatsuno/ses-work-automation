import json
import time

import numpy as np
from sentence_transformers import SentenceTransformer

print("Loading ruri-v3-30m model...")
t0 = time.time()
model = SentenceTransformer("cl-nagoya/ruri-v3-30m")
print(f"Model loaded in {time.time() - t0:.1f}s")

# データ読み込み
with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\poc_engineers.json", "r", encoding="utf-8") as f:
    engineers = json.load(f)
with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\poc_projects.json", "r", encoding="utf-8") as f:
    projects = json.load(f)


# エンジニアのテキスト生成（スキル+詳細情報）
def eng_text(e):
    parts = []
    if e["skills"]:
        parts.append(f"スキル: {e['skills']}")
    if e["detail"]:
        parts.append(e["detail"][:500])
    if e["price"]:
        parts.append(f"単価: {e['price']}万円")
    return " ".join(parts) if parts else "データなし"


# 案件のテキスト生成
def proj_text(p):
    parts = []
    if p["name"]:
        parts.append(p["name"])
    if p["skills"]:
        parts.append(f"必須スキル: {p['skills']}")
    if p["detail"]:
        parts.append(p["detail"][:500])
    if p["price"]:
        parts.append(f"単価: {p['price']}万円")
    return " ".join(parts) if parts else "データなし"


# ruri-v3用prefix
eng_texts = [f"検索クエリ: {eng_text(e)}" for e in engineers]
proj_texts = [f"検索対象: {proj_text(p)}" for p in projects]

print(f"エンジニア: {len(eng_texts)}件, 案件: {len(proj_texts)}件")

# Embedding生成
print("Generating engineer embeddings...")
t0 = time.time()
eng_embs = model.encode(eng_texts, show_progress_bar=False, batch_size=32)
print(f"Engineer embeddings done in {time.time() - t0:.1f}s")

print("Generating project embeddings...")
t0 = time.time()
proj_embs = model.encode(proj_texts, show_progress_bar=False, batch_size=32)
print(f"Project embeddings done in {time.time() - t0:.1f}s")

# コサイン類似度で全組み合わせ計算
from numpy.linalg import norm


def cosine_sim_matrix(A, B):
    A_norm = A / norm(A, axis=1, keepdims=True)
    B_norm = B / norm(B, axis=1, keepdims=True)
    return A_norm @ B_norm.T


print("Computing similarity matrix...")
sim_matrix = cosine_sim_matrix(np.array(proj_embs), np.array(eng_embs))
# sim_matrix[i][j] = 案件i と エンジニアj の類似度

# 各案件の上位N件を確認
results = []
for i, proj in enumerate(projects):
    scores = sim_matrix[i]
    top_indices = np.argsort(scores)[::-1]
    top_n = []
    for idx in top_indices[:15]:
        top_n.append(
            {
                "engineer": engineers[idx]["name"] or engineers[idx]["skills"][:30],
                "score": float(scores[idx]),
                "skills": engineers[idx]["skills"][:60],
            }
        )
    results.append({"project": proj["name"][:50], "project_skills": proj["skills"], "top15": top_n})

# 結果表示（最初の5案件）
print("\n" + "=" * 70)
print("=== embedding類似度 上位マッチ結果 ===")
print("=" * 70)
for r in results[:5]:
    print(f"\n案件: {r['project']}")
    print(f"  必須スキル: {r['project_skills']}")
    for j, t in enumerate(r["top15"][:10], 1):
        print(f"  {j}位: score={t['score']:.3f} | {t['engineer']} | {t['skills']}")

# 統計
all_scores = sim_matrix.flatten()
print("\n=== 全体統計 ===")
print(f"類似度 平均: {np.mean(all_scores):.3f}")
print(f"類似度 中央: {np.median(all_scores):.3f}")
print(f"類似度 std:  {np.std(all_scores):.3f}")
print(f"類似度 max:  {np.max(all_scores):.3f}")
print(f"類似度 min:  {np.min(all_scores):.3f}")

# 上位N件に絞ったときの閾値分析
for n in [3, 5, 10, 15]:
    thresholds = []
    for i in range(len(projects)):
        scores = sim_matrix[i]
        sorted_scores = np.sort(scores)[::-1]
        thresholds.append(sorted_scores[min(n - 1, len(sorted_scores) - 1)])
    avg_th = np.mean(thresholds)
    min_th = np.min(thresholds)
    print(f"上位{n:2d}件の閾値: 平均={avg_th:.3f}, 最低={min_th:.3f}")

# 結果保存
with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\poc_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("\n結果保存: poc_results.json")
