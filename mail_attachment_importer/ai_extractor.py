"""
ai_extractor.py - Claude APIでスキルシートから構造化データ抽出モジュール
"""
import json
import logging
import os
from datetime import date
from dotenv import load_dotenv

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
logger = logging.getLogger(__name__)

SKILL_OPTIONS = [
    "Java", "Python", "PHP", "JavaScript", "TypeScript", "C#", "Node.js", "React",
    "AWS", "インフラ", "PostgreSQL", "Oracle", "Vue.js", "MySQL", "Swift", "Azure",
    "Linux", "Go", "Ruby", "Docker", "MongoDB", "Spring"
]

ENGINEER_SYSTEM_PROMPT = f"""あなたはSESエンジニアのスキルシートから情報を抽出するAIです。
以下のテキストから全エンジニアの情報を抽出し、JSON配列で返してください。
JSON以外のテキストは一切出力しないでください。

抽出するJSON形式:
[
  {{
    "name": "氏名（フルネーム）",
    "price": 単価の数値（万円、不明はnull）,
    "available_date": "稼働可能日（YYYY-MM-DD形式、即日は今日の日付、不明はnull）",
    "experience_years": 経験年数の数値（不明はnull）,
    "skills": ["スキル1", "スキル2", ...]
  }}
]

スキルは以下のリストから該当するものだけを選んでください:
{", ".join(SKILL_OPTIONS)}
"""

PROJECT_SYSTEM_PROMPT = f"""あなたはSES案件情報を抽出するAIです。
以下のテキストから全案件の情報を抽出し、JSON配列で返してください。
JSON以外のテキストは一切出力しないでください。

抽出するJSON形式:
[
  {{
    "name": "案件名",
    "required_skills": ["必須スキル1", "必須スキル2"],
    "optional_skills": ["尚可スキル1"],
    "price": 単価の数値（万円、不明はnull）,
    "start_date": "開始日（YYYY-MM-DD形式、不明はnull）",
    "location": "勤務地（不明はnull）",
    "remote": "可 or 不可 or 一部リモート or unknown",
    "period": "期間（不明はnull）",
    "note": "その他補足情報"
  }}
]

スキルは以下のリストから該当するものだけを選んでください:
{", ".join(SKILL_OPTIONS)}
"""

CLASSIFY_SYSTEM_PROMPT = """あなたはSES業界のメール添付ファイルの内容を分類するAIです。
以下のテキストが「人員情報（スキルシート・経歴書）」か「案件情報（募集要項）」かを判定してください。
以下のJSONのみを返してください（説明文不要）:
{"type": "engineer"} または {"type": "project"} または {"type": "unknown"}

判断基準:
- 人員: 氏名・経験年数・スキル・稼働可能日・希望単価が主体
- 案件: 業務内容・必須スキル・期間・勤務地・募集単価が主体
"""


def classify_content(text: str) -> str:
    """
    テキストが人員情報か案件情報かを分類。

    Returns:
        "engineer" / "project" / "unknown"
    """
    import anthropic

    def fallback_classify() -> str:
        engineer_words = ["氏名", "経験年数", "経歴", "スキルシート", "稼働可能", "希望単価"]
        project_words = ["必須スキル", "募集", "案件", "勤務地", "期間", "業務内容"]
        engineer_score = sum(1 for word in engineer_words if word in text)
        project_score = sum(1 for word in project_words if word in text)
        if engineer_score > project_score:
            return "engineer"
        if project_score > engineer_score:
            return "project"
        return "unknown"

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return fallback_classify()

    client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=50,
            system=CLASSIFY_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": text[:3000]}]
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        data = json.loads(raw)
        content_type = data.get("type", "unknown")
        if content_type not in {"engineer", "project", "unknown"}:
            return fallback_classify()
        return content_type
    except Exception as e:
        logger.error(f"classify_content失敗: {e}")
        return fallback_classify()


def extract_engineers(text: str, filename: str) -> list:
    """
    スキルシートテキストからエンジニア情報をClaude APIで抽出。

    Returns:
        list of dict: [{"name", "price", "available_date", "experience_years", "skills"}, ...]
        失敗時は空リスト
    """
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY が .env に設定されていません")

    client = anthropic.Anthropic(api_key=api_key)

    today = date.today().isoformat()
    user_content = f"今日の日付: {today}\n\n以下のスキルシートから情報を抽出してください:\n\n{text[:8000]}"

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            system=ENGINEER_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}]
        )
        raw = response.content[0].text.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        engineers = json.loads(raw)
        if not isinstance(engineers, list):
            engineers = [engineers]

        logger.info(f"抽出成功: {filename} → {len(engineers)}名")
        return engineers

    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失敗: {filename} - {e}")
        return []
    except Exception as e:
        logger.error(f"Claude API呼び出し失敗: {filename} - {e}")
        return []


def extract_projects(text: str, filename: str) -> list:
    """
    案件情報テキストからプロジェクト情報をClaude APIで抽出。
    スプレッドシートに複数案件がまとまっているパターンに対応。

    Returns:
        list of dict: [{"name", "required_skills", "optional_skills", "price", ...}, ...]
        失敗時は空リスト
    """
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY が .env に設定されていません")

    client = anthropic.Anthropic(api_key=api_key)

    today = date.today().isoformat()
    user_content = f"今日の日付: {today}\n\n以下のテキストから案件情報を抽出してください:\n\n{text[:8000]}"

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            system=PROJECT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}]
        )
        raw = response.content[0].text.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        projects = json.loads(raw)
        if not isinstance(projects, list):
            projects = [projects]

        logger.info(f"案件抽出成功: {filename} → {len(projects)}件")
        return projects

    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失敗（案件）: {filename} - {e}")
        return []
    except Exception as e:
        logger.error(f"Claude API呼び出し失敗（案件）: {filename} - {e}")
        return []


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sample = """
氏名: 山田太郎
経験年数: 5年
希望単価: 65万円
稼働可能: 即日
スキル: Java, Spring, Oracle, Linux
"""
    result = extract_engineers(sample, "sample.txt")
    print(json.dumps(result, ensure_ascii=False, indent=2))
