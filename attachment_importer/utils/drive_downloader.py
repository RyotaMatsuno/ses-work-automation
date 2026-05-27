# -*- coding: utf-8 -*-
"""Google SpreadsheetをExcelとしてダウンロードする。"""

import os, re, requests
from pathlib import Path


def extract_file_id(url: str) -> str:
    m = re.search(r'/spreadsheets/d/([a-zA-Z0-9_-]+)', url)
    if m:
        return m.group(1)
    raise ValueError(f"SpreadsheetのURLからIDを抽出できませんでした: {url}")


def download_spreadsheet(url: str, save_dir: str) -> str:
    """
    GoogleスプレッドシートをExcel形式でダウンロードし、保存パスを返す。
    認証不要の公開シートのみ対応。認証が必要な場合はValueErrorを送出。
    """
    file_id = extract_file_id(url)
    export_url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    resp = requests.get(export_url, timeout=30, allow_redirects=True)
    if resp.status_code == 401 or 'accounts.google.com' in resp.url:
        raise ValueError("このスプレッドシートは認証が必要です。URLのみNotionに保存します。")
    resp.raise_for_status()
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, f"{file_id}.xlsx")
    with open(save_path, 'wb') as f:
        f.write(resp.content)
    return save_path
