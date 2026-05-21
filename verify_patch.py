with open('freee/freee_invoice_v2.py', encoding='utf-8') as f:
    c = f.read()
if 'auto_status_update' in c:
    idx = c.find('auto_status_update')
    print('組み込み確認OK')
    print(c[idx-100:idx+400])
else:
    print('NG')
