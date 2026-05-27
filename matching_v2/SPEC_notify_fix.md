# SPEC: notify_line.py バグ修正

## 目的
notify_line.py の2つのバグを修正する。

## バグ1: 岡本のLINE送信に松野のchannelトークンを使っている
### 現状
`build_line_accounts()` で松野・岡本ともに同じ `LINE_CHANNEL_ACCESS_TOKEN` を使っている。

### 修正
- 岡本には `OKAMOTO_LINE_CHANNEL_ACCESS_TOKEN` 環境変数を使う
- 環境変数がセットされていない場合は `LINE_CHANNEL_ACCESS_TOKEN` にフォールバック（後方互換性）

## バグ2: Notion API タイムアウトが短すぎる
### 現状
`get_assignee()` と `get_page_info()` の `requests.get(..., timeout=10)` が10秒で、
Notion APIが遅い時にタイムアウトしてクラッシュする。

### 修正
- 両関数の `timeout=10` を `timeout=30` に変更する

## 修正対象ファイル
`matching_v2/notify_line.py`

## 修正方法
- `get_assignee()` 関数内の `timeout=10` → `timeout=30`
- `get_page_info()` 関数内の `timeout=10` → `timeout=30`
- `build_line_accounts()` 関数で岡本のchannel_tokenを `OKAMOTO_LINE_CHANNEL_ACCESS_TOKEN` 優先にする
  ```python
  OKAMOTO: {
      "channel_token": os.environ.get("OKAMOTO_LINE_CHANNEL_ACCESS_TOKEN") or os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", ""),
      "user_id": os.environ.get("OKAMOTO_LINE_USER_ID", ""),
  },
  ```

## 完了条件
- `python matching_v2/notify_line.py --dry-run` が正常終了すること
