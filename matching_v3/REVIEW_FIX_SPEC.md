# SPEC: matching_v3 REVIEW率改善

## 背景
Phase 0実行結果：REVIEW率96%（目標<30%）
主因2つを確認済み：
1. extraction_confidence閾値が0.7と厳しすぎる（conf=0.4〜0.6のペアが多数REVIEW落ち）
2. ambiguous_skillsにSES案件で普通に出るスキルが混入してREVIEWになっている

## タスク1: matcher.py の信頼度閾値を緩和

### 変更箇所
ファイル: `matcher.py`
対象行: `conf < 0.7` の条件

### 変更内容
```python
# 変更前
if conf < 0.7:
    reasons.append(f"信頼度低: {conf:.2f}")

# 変更後
if conf < 0.5:
    reasons.append(f"信頼度低: {conf:.2f}")
```

## タスク2: structurer.py の SYSTEM_PROMPT ambiguous_skills定義を修正

### 問題
現在のSYSTEM_PROMPTでは以下がambiguous_skillsに分類される：
- 「リーダー経験」「技術力」「開発経験」→ SES案件で普通に出る→ ambiguousにすべきでない
- 「LLM」「AI活用」→ 近年SES案件で具体的技術として使われる→ required_skillsに入れるべき
- 「営業経験」「インサイドセールス経験」→ SES案件では出てこない非エンジニア系→ ambiguousのままでよい

### 変更内容
SYSTEM_PROMPT内の ambiguous_skills の定義を以下のように修正：

**ambiguous_skills に入れるもの（ソフトスキル・非技術系のみ）:**
- コミュニケーション能力、主体性、当事者意識 等の人物スキル
- 営業経験、インサイドセールス経験 等の非エンジニア職種経験
- 上流から一気通貫 等の抽象的な工程表現

**ambiguous_skills に入れないもの（required_skillsまたはoptional_skillsへ）:**
- 具体的技術: LLM, AI活用, クラウド, Docker, Kubernetes 等
- 工程経験: 要件定義経験, 設計経験, リーダー経験, PM経験 等
- 開発経験全般: 開発経験, Webアプリ開発経験 等

## 確認方法
修正後にpytestを実行して全テストがpassすること：
```
cd matching_v3
pytest tests/ -v
```

## 注意事項
- SYSTEM_PROMPTはUTF-8で記載すること
- 既存のテストを壊さないこと
- config.pyは変更しないこと
