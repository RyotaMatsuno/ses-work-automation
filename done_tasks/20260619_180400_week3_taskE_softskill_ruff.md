# 【Cursor作業指示】Week3 Task E: soft-skill all-pass + Ruff/pyright導入

対象ディレクトリ: ses_work/
作業内容: (1)承認済みソフトスキル判定実装 (2)コード品質ツール導入
完了条件: soft-skill実装+テスト、ruff check/pyright basicが通ること
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 修正1: soft-skill all-pass実装

### 問題
承認済み方針「ヒューマン/ソフトスキルは全員○」が未実装。
PM/コミュ力等がambiguous_skillsとしてREVIEWトリガーか語彙外パスでMATCH化。

### 修正方針
1. config/soft_skills.json にソフトスキル一覧を定義:
   ["コミュニケーション", "リーダーシップ", "PM経験", "マネジメント", "折衝", "調整", ...]
2. matcher.py の judge() で必須スキル判定前にソフトスキルフィルタ:
   ソフトスキルに該当する必須は全員○（チェック対象外にする）
3. テスト: 必須「PM経験」→ 全員○（チェックしない）

---

## 修正2: Ruff + pyright導入

### 手順
1. pyproject.toml に以下を追加:
```toml
[tool.ruff]
target-version = "py312"
line-length = 120
[tool.ruff.lint]
select = ["E", "F", "W", "I"]
ignore = ["E501"]  # 段階的に解除

[tool.pyright]
pythonVersion = "3.12"
typeCheckingMode = "basic"
```

2. ruff check --fix . で既存コードを一括修正（動作は変わらない）
3. ruff format . で整形
4. pyright basic で型エラー数を記録（修正はしない、現状把握のみ）
5. .pre-commit-config.yaml を作成:
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

### 注意
- 既存コードの型エラーは修正しない（数を記録するだけ）
- 新規コードにはtype hint必須のルールを維持
- ruff fixで動作が変わるケースがないか既存テストで確認

---

## 共通ルール
- 既存テスト全パス
