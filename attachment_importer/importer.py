# -*- coding: utf-8 -*-
"""
attachment_importer - メインスクリプト。
人員情報テキスト + ファイルを解析してNotionエンジニアDBに登録する。

使用例:
  python attachment_importer/importer.py --text "..." --file sheet.xlsx --source "松野LINE"
  python attachment_importer/importer.py --text "..." --spreadsheet-url "https://..." --source "岡本メール"
  python attachment_importer/importer.py --text "..." --file sheet.xlsx --source "松野LINE" --dry-run
"""

import argparse, json, logging, os, sys
from datetime import datetime
from pathlib import Path

# パス解決
BASE_DIR = Path(__file__).parent
SES_WORK_DIR = BASE_DIR.parent
sys.path.insert(0, str(SES_WORK_DIR))

try:
    from dotenv import dotenv_values
    _env = dotenv_values(SES_WORK_DIR / "config" / ".env")
    for k, v in _env.items():
        if k not in os.environ and v:
            os.environ[k] = v
except Exception:
    pass

from attachment_importer.parsers.text_parser import parse_text
from attachment_importer.parsers.file_parser import parse_file, extract_text_from_file
from attachment_importer.utils.drive_downloader import download_spreadsheet
from attachment_importer.utils.notion_writer import upsert_engineer

import requests

NOTION_VERSION = "2022-06-28"
LOG_PATH = BASE_DIR / "import.log"
FAILED_PATH = BASE_DIR / "failed_imports.json"
DOWNLOAD_DIR = str(BASE_DIR / "downloaded_files")

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def build_notion_headers() -> dict:
    api_key = os.environ.get("NOTION_API_KEY", "")
    if not api_key:
        raise RuntimeError("NOTION_API_KEY が設定されていません")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def merge_records(text_records: list, file_records: list) -> list:
    """テキストとファイルの人員情報を氏名マッチングでマージ。"""
    if not file_records:
        return text_records
    if not text_records:
        return file_records

    merged = []
    used_file_idx = set()

    for tr in text_records:
        tname = (tr.get("name") or "").strip()
        best_idx, best_score = None, 0

        for i, fr in enumerate(file_records):
            if i in used_file_idx:
                continue
            fname = (fr.get("name") or "").strip()
            if not fname:
                continue
            # スコアリング: 完全一致=3, イニシャル一致=2, 部分一致=1
            if tname == fname:
                score = 3
            elif tname and fname and (tname in fname or fname in tname):
                score = 2
            elif tname and fname and tname[:3] == fname[:3]:
                score = 1
            else:
                score = 0

            if score > best_score:
                best_score, best_idx = score, i

        if best_idx is not None and best_score > 0:
            fr = file_records[best_idx]
            used_file_idx.add(best_idx)
            # ファイル情報優先でマージ
            combined = {**tr, **{k: v for k, v in fr.items() if v is not None}}
            combined["raw_text"] = tr.get("raw_text") or fr.get("raw_text") or ""
            merged.append(combined)
        else:
            merged.append(tr)

    # マッチしなかったファイルレコードを追加
    for i, fr in enumerate(file_records):
        if i not in used_file_idx and fr.get("name"):
            merged.append(fr)

    return merged


def run(text: str, file_path: str = None, spreadsheet_url: str = None,
        source: str = "松野LINE", dry_run: bool = False):
    """メイン処理。"""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    notion_headers = build_notion_headers()
    failed = []

    # テキスト解析
    logger.info(f"テキスト解析開始 source={source}")
    text_records = []
    try:
        text_records = parse_text(text, api_key)
        logger.info(f"テキスト解析完了: {len(text_records)}人分")
    except Exception as e:
        logger.error(f"テキスト解析失敗: {e}")

    # ファイル解析
    file_records = []
    actual_file_path = file_path
    drive_url = None

    if spreadsheet_url:
        drive_url = spreadsheet_url
        try:
            actual_file_path = download_spreadsheet(spreadsheet_url, DOWNLOAD_DIR)
            logger.info(f"スプレッドシートDL完了: {actual_file_path}")
        except Exception as e:
            logger.warning(f"スプレッドシートDL失敗（URLのみ保存）: {e}")
            actual_file_path = None

    if actual_file_path and os.path.exists(actual_file_path):
        try:
            file_records = parse_file(actual_file_path, api_key)
            logger.info(f"ファイル解析完了: {len(file_records)}人分 ({actual_file_path})")
        except Exception as e:
            logger.warning(f"ファイル解析失敗、テキスト情報のみで続行: {e}")

    # マージ
    records = merge_records(text_records, file_records)
    logger.info(f"マージ完了: {len(records)}人分")

    # Notion登録
    success_count = 0
    for record in records:
        name = record.get("name") or "（名前不明）"
        try:
            result = upsert_engineer(
                record=record,
                source=source,
                file_path=actual_file_path,
                drive_url=drive_url,
                headers=notion_headers,
                dry_run=dry_run,
            )
            action = result.get("action")
            if action == "dry_run":
                logger.info(f"[DRY-RUN] {name} → 登録スキップ スキル={[s['name'] for s in result.get('properties', {}).get('スキル', {}).get('multi_select', [])]}")
            elif action == "create":
                logger.info(f"[SUCCESS] {name} → 新規登録 page_id={result.get('page_id')}")
            elif action == "update":
                logger.info(f"[SUCCESS] {name} → 更新 page_id={result.get('page_id')}")
            elif action == "skip":
                logger.warning(f"[SKIP] {name} → {result.get('reason')}")
            success_count += 1
        except Exception as e:
            logger.error(f"[ERROR] {name} → Notion登録失敗: {e}")
            failed.append({"name": name, "error": str(e), "record": record})

    # 失敗ログ保存
    if failed:
        existing = []
        if FAILED_PATH.exists():
            try:
                existing = json.loads(FAILED_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass
        existing.extend(failed)
        FAILED_PATH.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.warning(f"{len(failed)}件の登録に失敗しました → {FAILED_PATH}")

    logger.info(f"完了: 成功={success_count} 失敗={len(failed)} 合計={len(records)}")
    return {"success": success_count, "failed": len(failed), "total": len(records)}


def main():
    parser = argparse.ArgumentParser(description="人員情報をNotionエンジニアDBに登録する")
    parser.add_argument("--text", required=True, help="人員情報テキスト（LINEメッセージ等）")
    parser.add_argument("--file", help="スキルシートファイルパス（.xlsx/.xls/.docx/.pdf）")
    parser.add_argument("--spreadsheet-url", help="GoogleスプレッドシートURL")
    parser.add_argument("--source", default="松野LINE",
                        choices=["松野LINE", "岡本LINE", "松野メール", "岡本メール", "共通メール"],
                        help="入力元ラベル")
    parser.add_argument("--dry-run", action="store_true", help="Notionに書かずログだけ出力")
    args = parser.parse_args()

    run(
        text=args.text,
        file_path=args.file,
        spreadsheet_url=args.spreadsheet_url,
        source=args.source,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
