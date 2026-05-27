import sys, json
sys.stdout.reconfigure(encoding='utf-8')

with open('google_credentials.json', encoding='utf-8') as f:
    data = json.load(f)

print("type:", data.get('type'), flush=True)
print("project_id:", data.get('project_id'), flush=True)
print("client_email:", data.get('client_email'), flush=True)
print("private_key_id:", data.get('private_key_id','')[:20], flush=True)
print("private_key exists:", bool(data.get('private_key')), flush=True)
