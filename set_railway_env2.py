import requests

TOKEN = "fbc5deef-ab29-4f5c-b7b8-6dc2cc2e9c81"
PROJECT_ID = "1346ecbb-17a9-4c6f-a6c1-f256c1c5564a"
SERVICE_ID = "484966c3-2d1c-4736-9f69-891f11a35128"
ENV_ID = "46e90371-2c0b-4108-aefa-385df6916300"

headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

# Railway GraphQL v2 で正しいmutation
url = "https://backboard.railway.app/graphql/v2"

new_vars = {
    "SESSALES_MAIL_PASSWORD": "te!rra!884568",
    "MATSUNO_MAIL_PASSWORD": "N88[uR5:Ro!]",
    "OKAMOTO_MAIL_PASSWORD": "Egk:8gB3dr",
}

# 全変数をまとめてupsert
mutation = """
mutation($input: VariableCollectionUpsertInput!) {
  variableCollectionUpsert(input: $input)
}
"""
variables_payload = {
    "input": {"projectId": PROJECT_ID, "serviceId": SERVICE_ID, "environmentId": ENV_ID, "variables": new_vars}
}

res = requests.post(url, headers=headers, json={"query": mutation, "variables": variables_payload})
print(f"status={res.status_code}")
print(res.text[:500])
