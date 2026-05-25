# Cloudflare Tunnel セットアップ

1. cloudflaredをインストール: `winget install Cloudflare.cloudflared`
2. ログイン: `cloudflared tunnel login`
3. トンネル作成: `cloudflared tunnel create jobz-command`
4. 発行されたTUNNEL_IDを `config.yml` に記入
5. `start_tunnel.bat` を実行（またはスタートアップに登録）
6. 表示されたURL（trycloudflare.com）を `.env` の `JOBZ_COMMAND_URL` に記入
7. Cloud Runを再デプロイ: `gcloud run deploy ...`
