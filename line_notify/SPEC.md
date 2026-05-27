# SPEC.md - result.json LINE通知スクリプト

## 目的
matching_v2が生成した `ses_work/matching_v2/result.json` の内容を
松野・岡本のLINEに通知する。

## 入力
- `ses_work/matching_v2/result.json`
  - 構造: [{project_id, project_name, project_url, candidates: [{engineer_name, score, price, needs_check, required, optional}]}]

## 出力
- 松野のLINEに全案件の通知メッセージを送信
- 岡本のLINEに全案件の通知メッセージを送信（同内容）

## メッセージフォーマット
```
【マッチング結果】YYYY-MM-DD HH:MM

■ {project_name}（{candidates数}名マッチ）
{Notionリンク}
  ① {engineer_name} /{price}万 [要確認] ← needs_check=Trueの場合のみ
  ② {engineer_name} /{price}万
  ...（上位3名まで表示、それ以上は「他N名」と表示）

■ 次の案件...
```

## 仕様詳細
- candidatesは score降順、同スコアはprice昇順でソート
- needs_check=True の場合は名前の後に「[要確認]」を付与
- 1通あたりの文字数が5000字を超える場合は複数メッセージに分割
- candidates が0名の案件は通知しない
- 送信先:
  - 松野: LINE_CHANNEL_ACCESS_TOKEN + MATSUNO_LINE_USER_ID
  - 岡本: OKAMOTO_LINE_CHANNEL_ACCESS_TOKEN + OKAMOTO_LINE_USER_ID

## 実行方法
```
python notify_line.py
python notify_line.py --dry-run  # 送信せずコンソール出力のみ
```

## エラーハンドリング
- result.jsonが存在しない場合: エラーメッセージを出力して終了
- LINE API送信失敗: エラー内容を出力して続行（片方失敗でも他方は送信）
- 環境変数未設定: 警告出力してskip（dry-runは動作する）
