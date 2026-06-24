# SPEC.md - Phase6 Cloud Run SMTP環境変数設定

## 問題
webhook_server.py の send_email_via_callback() が参照する環境変数名と、
Cloud Runに設定すべき環境変数名がずれているため、Cloud Run上でメール送信が失敗する。

## 現状のコード（Line 1025〜1033）
```python
accounts_cfg = {
    'matsuno': {'user': 'r-matsuno@terra-ltd.co.jp', 'pw': os.environ.get('MATSUNO_MAIL_PASSWORD', os.environ.get('SESSALES_MAIL_PASSWORD', ''))},
    'okamoto': {'user': 'r-okamoto@terra-ltd.co.jp', 'pw': os.environ.get('OKAMOTO_MAIL_PASSWORD', os.environ.get('SESSALES_MAIL_PASSWORD', ''))},
    'sessales': {'user': 'sessales@terra-ltd.co.jp', 'pw': os.environ.get('SESSALES_MAIL_PASSWORD', '')},
}
```

## 修正内容
環境変数のフォールバックチェーンを充実させる。
各アカウントのpwに、.envで使われているキー名も追加でフォールバックとして参照させる。

```python
accounts_cfg = {  # [Phase6] フォールバックキー追加
    'matsuno': {
        'user': 'r-matsuno@terra-ltd.co.jp',
        'pw': os.environ.get('MATSUNO_MAIL_PASSWORD')
              or os.environ.get('MATSUNO_PASSWORD')
              or os.environ.get('SESSALES_MAIL_PASSWORD', ''),
    },
    'okamoto': {
        'user': 'r-okamoto@terra-ltd.co.jp',
        'pw': os.environ.get('OKAMOTO_MAIL_PASSWORD')
              or os.environ.get('OKAMOTO_PASSWORD')
              or os.environ.get('SESSALES_MAIL_PASSWORD', ''),
    },
    'sessales': {
        'user': 'sessales@terra-ltd.co.jp',
        'pw': os.environ.get('SESSALES_MAIL_PASSWORD')
              or os.environ.get('SESSALES_PASSWORD', ''),
    },
}
```

## デプロイ時に設定するCloud Run環境変数（ジョブズが--update-env-varsで設定）
以下の3つをCloud Runに追加する（値はローカル.envから取得）:
- MATSUNO_MAIL_PASSWORD
- OKAMOTO_MAIL_PASSWORD
- SESSALES_MAIL_PASSWORD

## gcloudコマンド（ジョブズが実施）
コード修正後にジョブズがgcloud run services updateで環境変数を追加し、
その後 gcloud run deploy でソース再デプロイする。
