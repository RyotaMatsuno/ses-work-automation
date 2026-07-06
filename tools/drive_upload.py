# -*- coding: utf-8 -*-
"""
Google Drive に xlsx をアップロードし、Google Sheets に変換する。

使い方:
  python ses_work/tools/drive_upload.py [xlsxパス]
  デフォルト: ses_work/法人化設計マスター.xlsx
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

SES_WORK_DIR = Path(__file__).resolve().parent.parent
DEFAULT_XLSX = SES_WORK_DIR / "法人化設計マスター.xlsx"
FALLBACK_XLSX = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\法人化設計マスター.xlsx")

DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
]
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
SHEETS_MIME = "application/vnd.google-apps.spreadsheet"
TOKEN_URI = "https://oauth2.googleapis.com/token"


def _find_file(name: str, extra_dirs: tuple[Path, ...] = ()) -> Path | None:
    """ses_work/config/ 配下 → ses_work/ 直下 → 追加パスの順で検索。"""
    search_roots = (SES_WORK_DIR / "config", SES_WORK_DIR, *extra_dirs)
    for root in search_roots:
        if not root.exists():
            continue
        if root.is_file() and root.name == name:
            return root
        if root.is_dir():
            matches = sorted(root.rglob(name))
            if matches:
                return matches[0]
    return None


def _resolve_xlsx_path(arg: str | None) -> Path:
    if arg:
        path = Path(arg)
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"xlsx が見つかりません: {path}")
        return path

    for candidate in (DEFAULT_XLSX, FALLBACK_XLSX):
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "xlsx が見つかりません。次のいずれかを用意するか、パスを引数で指定してください:\n"
        f"  - {DEFAULT_XLSX}\n"
        f"  - {FALLBACK_XLSX}\n"
        "  例: python ses_work/tools/drive_upload.py path/to/file.xlsx"
    )


def _load_token_data(token_path: Path) -> dict:
    return json.loads(token_path.read_text(encoding="utf-8"))


def _save_token_data(token_path: Path, token_data: dict) -> None:
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(json.dumps(token_data, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_credentials(token_data: dict) -> Credentials:
    access_token = token_data.get("access_token") or token_data.get("token")
    scopes = token_data.get("scopes") or DRIVE_SCOPES
    return Credentials(
        token=access_token,
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri") or TOKEN_URI,
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=scopes,
    )


def _run_reauth(credentials_path: Path, token_path: Path) -> Credentials:
    print("再認証が必要です。ブラウザが開きます。", flush=True)
    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), DRIVE_SCOPES)
    creds = flow.run_local_server(port=0)
    token_path.write_text(creds.to_json(), encoding="utf-8")
    print(f"トークンを保存しました: {token_path}", flush=True)
    return creds


def _refresh_or_reauth(
    creds: Credentials,
    token_path: Path,
    token_data: dict,
    credentials_path: Path | None,
) -> Credentials:
    if not creds.refresh_token:
        if credentials_path is None:
            raise FileNotFoundError(
                "refresh_token があり、credentials.json も見つかりません。再認証できません:\n"
                f"  - {SES_WORK_DIR / 'config'}\n"
                f"  - {SES_WORK_DIR}"
            )
        return _run_reauth(credentials_path, token_path)

    try:
        creds.refresh(Request())
        token_data["access_token"] = creds.token
        token_data["token"] = creds.token
        _save_token_data(token_path, token_data)
        return creds
    except RefreshError as exc:
        print(f"トークンのリフレッシュに失敗しました: {exc}", flush=True)
        print(
            "再認証が必要です。credentials.json を使って OAuth2 フローを開始します。",
            flush=True,
        )
        if credentials_path is None:
            raise FileNotFoundError(
                "credentials.json が見つからないため再認証できません。次を確認してください:\n"
                f"  - {SES_WORK_DIR / 'config'}\n"
                f"  - {SES_WORK_DIR}\n"
                "OAuth2 クライアント ID (credentials.json) を配置後、再実行してください。"
            ) from exc
        return _run_reauth(credentials_path, token_path)


def get_credentials() -> Credentials:
    token_path = _find_file("token_sheets.json", extra_dirs=(SES_WORK_DIR / "sheets",))
    if token_path is None:
        raise FileNotFoundError(
            "token_sheets.json が見つかりません。次を確認してください:\n"
            f"  - {SES_WORK_DIR / 'config'}\n"
            f"  - {SES_WORK_DIR}"
        )

    credentials_path = _find_file("credentials.json", extra_dirs=(SES_WORK_DIR / "gmail",))
    token_data = _load_token_data(token_path)
    creds = _build_credentials(token_data)

    if creds.valid:
        return creds

    return _refresh_or_reauth(creds, token_path, token_data, credentials_path)


def upload_xlsx_as_sheet(xlsx_path: Path) -> str:
    token_path = _find_file("token_sheets.json", extra_dirs=(SES_WORK_DIR / "sheets",))
    credentials_path = _find_file("credentials.json", extra_dirs=(SES_WORK_DIR / "gmail",))
    creds = get_credentials()
    try:
        return _upload_with_credentials(creds, xlsx_path)
    except RefreshError:
        if token_path is None:
            raise
        token_data = _load_token_data(token_path)
        creds = _refresh_or_reauth(
            _build_credentials(token_data),
            token_path,
            token_data,
            credentials_path,
        )
        return _upload_with_credentials(creds, xlsx_path)


def _upload_with_credentials(creds: Credentials, xlsx_path: Path) -> str:
    service = build("drive", "v3", credentials=creds, cache_discovery=False)

    media = MediaFileUpload(
        str(xlsx_path),
        mimetype=XLSX_MIME,
        resumable=True,
    )
    body = {
        "name": xlsx_path.stem,
        "mimeType": SHEETS_MIME,
    }

    try:
        uploaded = (
            service.files()
            .create(
                body=body,
                media_body=media,
                fields="id,name,mimeType,webViewLink",
            )
            .execute()
        )
    except RefreshError as exc:
        raise RuntimeError(
            "認証トークンが無効です。次を実行して再認証してください:\n"
            f"  python {Path(__file__).resolve()}\n"
            f"詳細: {exc}"
        ) from exc
    except HttpError as exc:
        raise RuntimeError(f"Google Drive API エラー ({exc.resp.status}): {exc}") from exc

    file_id = uploaded["id"]
    sheets_url = f"https://docs.google.com/spreadsheets/d/{file_id}/edit"
    print(f"アップロード完了: {uploaded.get('name', xlsx_path.name)}", flush=True)
    print(f"mimeType: {uploaded.get('mimeType', SHEETS_MIME)}", flush=True)
    print(sheets_url, flush=True)
    return sheets_url


def main() -> int:
    try:
        xlsx_path = _resolve_xlsx_path(sys.argv[1] if len(sys.argv) > 1 else None)
        print(f"アップロード対象: {xlsx_path}", flush=True)
        upload_xlsx_as_sheet(xlsx_path)
        return 0
    except FileNotFoundError as exc:
        print(f"エラー: {exc}", file=sys.stderr, flush=True)
        return 1
    except RefreshError as exc:
        print(
            "エラー: 認証トークンの更新に失敗しました。ブラウザで再認証してください。\n"
            f"  python {Path(__file__).resolve()}\n"
            f"詳細: {exc}",
            file=sys.stderr,
            flush=True,
        )
        return 1
    except RuntimeError as exc:
        print(f"エラー: {exc}", file=sys.stderr, flush=True)
        return 1
    except Exception as exc:
        print(f"予期しないエラー: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
