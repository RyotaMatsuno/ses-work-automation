# 新PC引き継ぎ手順書

作成日: 2026-04-24
※新PCのユーザー名: ma_py（旧PCと同じなのでパス変更不要）

---

## 全体の流れ

1. 必須ソフトをインストール
2. ses_workフォルダの確認（OneDrive自動同期）
3. Claude Desktopをセットアップ
4. タスクスケジューラを再設定
5. 動作確認

所要時間: 約30〜40分

---

## STEP1: 必須ソフトのインストール

### Python
1. https://www.python.org/downloads/ を開く
2. 「Download Python」をクリック
3. インストール時に**「Add Python to PATH」に必ずチェックを入れる**（重要）
4. インストール後にコマンドプロンプト（Windowsキー+R → cmd → Enter）で確認:
   ```
   python --version
   ```

### Node.js
1. https://nodejs.org/ を開く
2. LTS版をダウンロードしてインストール
3. 確認:
   ```
   node --version
   ```

### Git
1. https://git-scm.com/download/win を開く
2. ダウンロードしてインストール（設定はデフォルトでOK）
3. 確認:
   ```
   git --version
   ```

### Claude Desktop
1. https://claude.ai/download を開く
2. ダウンロードしてインストール
3. インストール後はまだ設定しない（STEP3でやる）

### Pythonライブラリ
コマンドプロンプトで以下を実行:
```
pip install flask requests python-dotenv line-bot-sdk anthropic
```

---

## STEP2: ses_workフォルダの確認

OneDriveにログインして同期が完了するのを待つ。
デスクトップに `ses_work` フォルダが現れたらOK。

OneDriveのサインイン:
- タスクバー右下のOneDriveアイコンをクリック
- 旧PCと同じMicrosoftアカウントでログイン

---

## STEP3: Claude Desktopのセットアップ

### 3-1. 設定ファイルを作る場所を開く

Windowsキー+R → 以下を貼り付けてEnter:
```
%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude
```

※フォルダが見つからない場合はClaude Desktopを一度起動して終了すると作られる。

### 3-2. claude_desktop_config.jsonを作る

フォルダの中で右クリック→新規作成→テキストドキュメント
→ファイル名を `claude_desktop_config.json` にする（.txtを消す）
→メモ帳で開いて以下を丸ごとコピペして保存:

```json
{
  "mcpServers": {
    "notion": {
      "command": "C:\\Program Files\\nodejs\\npx.cmd",
      "args": [
        "-y",
        "@notionhq/notion-mcp-server"
      ],
      "env": {
        "OPENAPI_MCP_HEADERS": "{\"Authorization\": \"Bearer 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\", \"Notion-Version\": \"2022-06-28\"}"
      }
    },
    "playwright": {
      "command": "C:\\Program Files\\nodejs\\npx.cmd",
      "args": [
        "-y",
        "@playwright/mcp",
        "--output-dir",
        "C:\\Python_test\\.playwright-mcp"
      ]
    },
    "filesystem": {
      "command": "C:\\Program Files\\nodejs\\npx.cmd",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "C:\\Users\\ma_py\\OneDrive\\デスクトップ\\ses_work",
        "C:\\Python_test",
        "C:\\Users\\ma_py\\AppData\\Roaming\\Claude",
        "C:\\Users\\ma_py\\AppData\\Local"
      ]
    },
    "ses-mail": {
      "command": "python",
      "args": [
        "C:\\Users\\ma_py\\OneDrive\\デスクトップ\\ses_work\\mail_mcp\\mail_server.py"
      ],
      "env": {
        "MATSUNO_MAIL_PASSWORD": "N88[uR5:Ro!]",
        "OKAMOTO_MAIL_PASSWORD": "Egk:8gB3dr"
      }
    }
  }
}
```

### 3-3. 設定をClaude本来の場所にもコピー

旧PCと同様に `update_config.py` を使って反映させる。
`ses_work` フォルダの `update_config.py` をダブルクリック。
→「コピー成功」と表示されたらOK。

### 3-4. Claude Desktopを起動して動作確認

Claudeチャットで以下を送る:
```
ses_workフォルダの中身を見せて
```
→ ファイル一覧が返ってきたらFilesystem MCPが動いている。

---

## STEP4: タスクスケジューラの再設定

旧PCのタスクスケジューラは新PCに引き継がれない。1回だけ再設定が必要。

`ses_work` フォルダの `setup_all_tasks.bat` をダブルクリックするだけ。
→ Outlook自動取得（毎日9h/13h/18h）とFreee請求書自動生成（毎月25日）が設定される。

---

## STEP5: 動作確認チェックリスト

Claudeチャットで以下を順番に試す:

| 確認内容 | Claudeに送るメッセージ | 期待する結果 |
|---|---|---|
| Filesystem | `ses_workフォルダの中身を見せて` | ファイル一覧が返る |
| Notion | `エンジニアDBの件数教えて` | 件数が返る |
| メールMCP | `松野アドレスの最新メール5件見せて` | メール一覧が返る |

---

## 注意事項

- `config/.env` のAPIキーはOneDrive経由でそのまま引き継がれる（追加作業不要）
- Railway・Notion・GitHubはクラウドなので新PCで何もしなくていい
- Claude.aiのアカウントは同じアカウントでログインすれば会話履歴もそのまま

---

## 困ったときはジョブズに相談

Claudeに「新PCセットアップで○○がうまくいかない」と送ればOK。
