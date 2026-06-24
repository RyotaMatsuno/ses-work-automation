# matching_v3 コードレビュー依頼（nano移行後の最終検証）

**背景**: SES事業向けマッチングシステムのLLMをAnthropic Haiku → gpt-4.1-nanoに移行し、直前セッションで5件のバグを修正した。本番稼働前の最終コードレビューを依頼する。

---

## 直前セッションで修正したバグ（5件）

| # | 内容 | 修正内容 |
|---|---|---|
| 1 | sys.path競合（structurer.pyがルートのcost_guard.pyを読んでいた） | matching_v3/をsys.pathの最優先に変更 |
| 2 | 案件DBクエリ400（`登録日時`プロパティ不在） | `created_time`（Notionシステムフィールド）に変更 |
| 3 | エンジニアDBクエリ400（`提案対象フラグ`不在） | フィルター除去＋日付形式修正 |
| 4 | ゾンビプロセス並走（テスト多重起動でロックすり抜け） | LockFileにstale判定（30分）を追加 |
| 5 | Notion書き戻し400（`業務ステータス`誤記＋選択肢外の値） | `ステータス`プロパティに修正、MATCH/REVIEW時のみ「選考中」に更新 |

修正後の実行結果: **Anthropic呼び出しゼロ、OpenAI(nano) 200が16件、Notion PATCH 200**

---

## 現在のファイル構成

```
matching_v3/
  config.py          # 設定ロード（DEFAULT_STRUCTURER_MODEL = "gpt-4.1-nano"）
  cost_guard.py      # コスト防御壁（日次$6/月次$140上限）
  structurer.py      # LLM呼び出し（nano/Anthropicを振り分け）
  matcher.py         # Pythonマッチングロジック（LLM不使用）
  notifier.py        # LINE通知（Push API）
  notion_client.py   # Notion REST APIラッパー
  matching_v3.py     # エントリーポイント（スケジューラ経由で毎朝8時実行）
  processed_db.py    # SQLite処理ステータス管理
  skill_aliases.json # スキル正規化辞書
  users.yaml         # LINE送信先設定
```

---

## レビューを依頼したいコード

### 1. config.py（変更箇所のみ）
```python
DEFAULT_STRUCTURER_MODEL = "gpt-4.1-nano"

class Config:
    def __init__(self, ...):
        ...
        self.structurer_model = os.environ.get(
            "STRUCTURER_MODEL",
            self.env.get("STRUCTURER_MODEL") or DEFAULT_STRUCTURER_MODEL,
        )
```

### 2. cost_guard.py（主要部分）
```python
class CostGuard:
    DAILY_CALL_LIMIT = 1500
    DAILY_COST_LIMIT_USD = 6.00
    MONTHLY_DEGRADE_USD = 120.00
    MONTHLY_STOP_USD = 140.00
    HAIKU_INPUT_RATE = 0.10 / 1_000_000   # gpt-4.1-nanoのinput単価
    HAIKU_OUTPUT_RATE = 0.40 / 1_000_000  # gpt-4.1-nanoのoutput単価

    def get_model(self) -> str:
        from config import DEFAULT_STRUCTURER_MODEL
        return os.environ.get("STRUCTURER_MODEL", DEFAULT_STRUCTURER_MODEL)
```
※注: 変数名が`HAIKU_*`のままだが実態はnanoのレート

### 3. structurer.py（振り分けロジック）
```python
def structure(body: str, cost_guard: CostGuard, config: Config | None = None) -> dict[str, Any]:
    cfg = config or Config()
    ...
    model = cost_guard.get_model()
    if model.startswith("gpt-") or model.startswith("o1") or model.startswith("o3"):
        response = _call_openai(prompt_text, model, cfg)
    else:
        response = _call_anthropic(prompt_text, model, cfg)
    ...

def _call_openai(prompt_text: str, model: str, config: Config):
    from openai import OpenAI
    api_key = config.get("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        max_tokens=2000,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text},
        ],
    )
    return resp
```

### 4. matcher.py（判定ロジック）
```python
def judge(case_json: dict, engineer: dict, normalizer: SkillNormalizer) -> tuple[str, list[str]]:
    reasons: list[str] = []

    # 単価チェック: 粗利 < 5万 → NG
    eng_price = float(engineer.get("単価（万円）") or 0)
    case_max = float(case_json.get("price_max") or 0)
    if case_max > 0 and eng_price > 0:
        gross = case_max - eng_price
        if gross < 5.0:
            return "NG", [f"粗利不足: ..."]

    # 必須スキル: 1つでも不足 → NG
    required_raw = case_json.get("required_skills") or []
    eng_skills = set(engineer.get("スキル") or [])
    missing = []
    for skill in required_raw:
        normalized = normalizer.normalize(skill)
        if normalized is None:
            reasons.append(f"未登録必須スキル要確認: {skill}")
        elif normalized not in eng_skills:
            missing.append(normalized)
    if missing:
        return "NG", [f"必須スキル不足: {missing}"]

    # 並行スコア: >= 5.0 → NG（判断マニュアル準拠）
    p_score = _calc_parallel_score(engineer)
    if p_score >= 5.0:
        return "NG", [f"並行過多: スコア{p_score:.1f}（上限5.0）"]

    # 情報鮮度: 21日超 → REVIEW
    last_edit = engineer.get("_last_edited_time", "")
    if last_edit and _days_since(last_edit) > 21:
        reasons.append(f"エンジニア情報古い（{_days_since(last_edit)}日前更新）")

    # ambiguous_skills → REVIEW
    if case_json.get("ambiguous_skills"):
        reasons.append(f"曖昧スキルあり: {case_json['ambiguous_skills']}")

    # 構造化精度 < 0.3 → REVIEW
    conf = float(case_json.get("extraction_confidence", 1.0) or 0.0)
    if conf < 0.3:
        reasons.append(f"構造化精度低: {conf:.2f}")

    if reasons:
        non_ambig = [r for r in reasons if not r.startswith("曖昧スキルあり")]
        if not non_ambig:
            return "MATCH", reasons   # ambiguousのみならMATCH
        return "REVIEW", reasons
    return "MATCH", []
```

### 5. notion_client.py（_parse_engineer_page）
```python
@staticmethod
def _parse_engineer_page(page: dict[str, Any]) -> dict[str, Any]:
    props = page.get("properties", {})
    return {
        "id": page.get("id", ""),
        "名前": _title(props.get("名前")),
        "スキル": _multi_select(props.get("スキル")),
        "単価（万円）": _number(props.get("単価（万円）")),
        "経験年数": _number(props.get("経験年数")),
        "稼働状況": _select(props.get("稼働状況")),    # ← 1行目
        "担当者": _select(props.get("担当者")),
        "稼働状況": _checkbox(props.get("稼働状況")),  # ← 2行目（重複キー！上書きされる）
        "備考（LINEメモ）": _rich_text(props.get("備考（LINEメモ）")),
        "_last_edited_time": page.get("last_edited_time", ""),
    }
```

---

## 自分で気づいた要確認点（GPTに判断してほしい）

### [Issue 1] `notion_client._parse_engineer_page` の重複キー
- `稼働状況` が2回定義されており、`_checkbox`（bool）が`_select`（str）を上書きしている
- **現状の影響**: `稼働状況`の値はmatcher.pyで使っていないため動作に支障なし（Notionフィルタで稼働中エンジニアのみ取得しているため）
- **質問**: このまま放置してよいか、今すぐ直すべきか（直すなら正しい方は`_select`か`_checkbox`か）

### [Issue 2] `cost_guard.HAIKU_INPUT_RATE` / `HAIKU_OUTPUT_RATE` の命名
- 変数名が`HAIKU_*`のままだが、設定値はgpt-4.1-nanoの単価（$0.10/$0.40 per 1Mトークン）
- 機能的な問題はない。リネームすべきか？

### [Issue 3] SPEC.md vs コードの乖離（並行スコア）
- SPEC.md §6.3では「並行スコア>=5.0 → reasonsに追加（REVIEWになる）」
- 実装では「並行スコア>=5.0 → 直接NG返却」
- **判断マニュアルv3 §5**: 「合計5.0以上 → 提案NG」と明記されており、**コードが正しい**
- SPECが古い。SPEC更新すべきか？

### [Issue 4] matcher.py の `ambiguous_skills` ロジック
- `ambiguous_skills`のみがreasonの場合 → MATCHとして扱う（`non_ambig`が空だからMATCH）
- これは意図的？（曖昧スキルのみなら問題ないという判断？）

---

## 質問サマリー

1. Issue 1-4について、今すぐ修正すべきものはどれか？優先順位を教えてほしい
2. nanoへの移行コード（structurer.py）に見落としているリスクはあるか？
3. LockFileのstale判定（30分）は適切か？もっと短い方がよいか？
4. 上記以外に本番稼働前に直すべき箇所があれば指摘してほしい

---

## 補足情報
- 実行環境: Windows 11 + Python 3.12
- スケジューラ: Windowsタスクスケジューラ（毎朝8:00、平日のみ）
- 月次コスト目標: $6以下（現実績 $2.9/月）
- 精度: fixtures.jsonの8/8テストケースで正解（nanoのfew-shot効果で達成）
