# SPEC_git_cleanup.md - GitHubプッシュブロック解消

最終更新: 2026-05-22

## 問題
GitHub Push Protection が過去のcommit (4e21f737) にある以下のファイルを検出してpushをブロックしている：
- gmail/credentials.json (Google OAuth Client ID/Secret)
- google_credentials.json (Google Cloud Service Account)
- ses-work-automation-170e12155a49.json (Google Cloud Service Account)
- deploy_cloudrun.bat (Anthropic API Key)
- local_server/server.log (Anthropic API Key)

## 解決方針
git filter-repo または BFG Repo Cleaner を使って過去のcommitから機密ファイルを削除する。

## 実装手順
1. pip install git-filter-repo
2. 問題のファイルをgit historyから削除：
   git filter-repo --path gmail/credentials.json --invert-paths --force
   git filter-repo --path google_credentials.json --invert-paths --force
   git filter-repo --path ses-work-automation-170e12155a49.json --invert-paths --force
3. deploy_cloudrun.bat の機密情報をredact
4. local_server/server.log をgit historyから削除
5. force push

## 注意
- filter-repoはcommit IDが全部変わるので実行前に松野に確認が必要
- 代替: GitHub UnblockURL経由でbypass reason="I'll fix it later"を選択してそのままpushする

## Codexへの指示
このSPECはCodexタスクではなく、松野への確認待ち事項として記録する。
実装は松野確認後に行う。

## 現状
- ローカルの変更（webhook_server.py修正）はcommit済み(426f5a4)
- pushのみブロックされている状態
- Railwayは現在の旧バージョンで稼働中
