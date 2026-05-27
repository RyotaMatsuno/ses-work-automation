# CLAUDE.md - propose_pipeline

## 目的
matching_v2のresult.jsonから提案メール下書きを自動生成し、ses-mailに下書き保存する。

## 禁止事項
- メールを実際に送信しない（下書き保存のみ）
- result.jsonを上書きしない（読み取り専用）
- Notion・LINEへの書き込みをしない
- 外部ライブラリを新規インストールしない（標準ライブラリ + dotenv + requests のみ使用可）

## 作業ルール
- SPEC.mdとTASKS.mdを必ず読んでから実装開始
- ファイルはすべてこのディレクトリ（propose_pipeline/）内に作成
- config/.envはses_workルートにある（dotenv_valuesで読み込む）
- 実行ディレクトリはses_workルート
