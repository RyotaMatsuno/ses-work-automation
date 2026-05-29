import base64
import io
import json
import os
import re
from datetime import datetime

import requests
from dotenv import dotenv_values


ENV_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', '.env')
if os.path.exists(ENV_PATH):
    config = dotenv_values(ENV_PATH)
    for key, value in config.items():
        if key not in os.environ:
            os.environ[key] = value

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')


def _extract_pdf_text(file_bytes):
    try:
        import pdfplumber

        texts = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                if text.strip():
                    texts.append(text)
        return "\n".join(texts)
    except Exception as e:
        print(f"[skill_extractor] pdf extract error: {e}")
        return ""


def _extract_xlsx_text(file_bytes):
    try:
        from openpyxl import load_workbook

        texts = []
        workbook = load_workbook(io.BytesIO(file_bytes), data_only=True, read_only=True)
        try:
            for sheet in workbook.worksheets:
                texts.append(f"[sheet: {sheet.title}]")
                for row in sheet.iter_rows(values_only=True):
                    values = [str(value) for value in row if value is not None and str(value).strip()]
                    if values:
                        texts.append("\t".join(values))
        finally:
            workbook.close()
        return "\n".join(texts)
    except Exception as e:
        print(f"[skill_extractor] xlsx extract error: {e}")
        return ""


def _extract_docx_text(file_bytes):
    try:
        from docx import Document

        document = Document(io.BytesIO(file_bytes))
        texts = [p.text for p in document.paragraphs if p.text and p.text.strip()]
        for table in document.tables:
            for row in table.rows:
                values = [cell.text.strip() for cell in row.cells if cell.text and cell.text.strip()]
                if values:
                    texts.append("\t".join(values))
        return "\n".join(texts)
    except Exception as e:
        print(f"[skill_extractor] docx extract error: {e}")
        return ""


def extract_skills_from_bytes(file_bytes, mime_type):
    try:
        mime_type = mime_type or ""
        if mime_type == "application/pdf":
            return _extract_pdf_text(file_bytes)
        if mime_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            return _extract_xlsx_text(file_bytes)
        if mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return _extract_docx_text(file_bytes)
        if mime_type.startswith("image/"):
            return base64.b64encode(file_bytes).decode("utf-8")

        for extractor in (_extract_pdf_text, _extract_xlsx_text, _extract_docx_text):
            text = extractor(file_bytes)
            if text.strip():
                return text
        return file_bytes.decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[skill_extractor] extract error: {e}")
        return ""


def _parse_json_text(text):
    try:
        cleaned = re.sub(r'```json|```', '', text or '').strip()
        match = re.search(r'\{.*\}', cleaned, re.S)
        if match:
            cleaned = match.group(0)
        data = json.loads(cleaned)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"[skill_extractor] json parse error: {e}")
        return {}


def analyze_skill_sheet_v2(file_bytes, mime_type, summary_text=""):
    try:
        extracted = extract_skills_from_bytes(file_bytes, mime_type)
        if not extracted:
            return {}

        current_year = datetime.now().year
        system = (
            "SES業界のスキルシート解析AI。JSON形式のみ返答。"
            "price=万円整数。experience_years=業界経験年数の整数。"
        )
        prompt = f"""スキルシートから人材情報をJSONのみで抽出してください。マークダウン不要。

現在年: {current_year}

出力形式:
{{"name":"","age":0,"experience_years":0,"price":0,"available_date":"YYYY-MM-DD or sokujitsu","location":"","affiliation":"","note":"","skills":[{{"name":"Java","years":20,"last_used_year":2025,"active":true}}]}}

スキルのactive判定:
- last_used_year が現在年から10年以上前（{current_year - 10}年以前）なら active=false
- last_used_year が不明で、スキルシートの職歴に一切登場しないなら active=false
- years が1年未満なら active=false
- 上記以外は active=true

summary_textがある場合は、スキルシート本文より優先して氏名・単価・稼働日・場所などを補完してください。
"""
        if mime_type and mime_type.startswith("image/"):
            content = [
                {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": extracted}},
                {"type": "text", "text": f"{prompt}\n\nsummary_text:\n{summary_text or ''}"}
            ]
        else:
            combined_text = "\n\n".join([t for t in [summary_text, extracted] if t])
            content = f"{prompt}\n\n入力:\n{combined_text[:50000]}"

        res = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-haiku-4-5-20251001", "max_tokens": 2000,
                  "system": system, "messages": [{"role": "user", "content": content}]},
            timeout=90
        )
        if res.status_code != 200:
            print(f"[skill_extractor] API error: {res.status_code} {res.text[:200]}")
            return {}

        data = res.json()
        usage = data.get("usage", {})
        print(f"[claude_api] caller=analyze_skill_sheet_v2 model=haiku max_tokens=2000 "
              f"in={usage.get('input_tokens','?')} out={usage.get('output_tokens','?')}")
        return _parse_json_text(data["content"][0]["text"])
    except Exception as e:
        print(f"[skill_extractor] analyze error: {e}")
        return {}


def filter_and_sort_skills(skills_list):
    try:
        from webhook_server import VALID_SKILLS

        valid_map = {skill.lower(): skill for skill in VALID_SKILLS}
        active_skills = []
        for item in skills_list or []:
            if not isinstance(item, dict) or not item.get("active"):
                continue
            name = str(item.get("name") or "").strip()
            normalized = valid_map.get(name.lower())
            if not normalized:
                continue
            try:
                years = float(item.get("years") or 0)
            except Exception:
                years = 0
            active_skills.append((normalized, years))

        sorted_names = []
        seen = set()
        for name, _ in sorted(active_skills, key=lambda x: x[1], reverse=True):
            if name not in seen:
                sorted_names.append(name)
                seen.add(name)
        return sorted_names
    except Exception as e:
        print(f"[skill_extractor] filter error: {e}")
        return []
