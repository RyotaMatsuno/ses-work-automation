
import requests

TOKEN = "fbc5deef-ab29-4f5c-b7b8-6dc2cc2e9c81"
SERVICE_ID = "484966c3-2d1c-4736-9f69-891f11a35128"
ENV_ID = "46e90371-2c0b-4108-aefa-385df6916300"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# 追加する環境変数
new_vars = {
    "SESSALES_MAIL_PASSWORD": "te!rra!884568",
    "MATSUNO_MAIL_PASSWORD": "N88[uR5:Ro!]",
    "OKAMOTO_MAIL_PASSWORD": "Egk:8gB3dr"
}

# Railway GraphQL API
url = "https://backboard.railway.app/graphql/v2"

for key, value in new_vars.items():
    mutation = """
    mutation UpsertVariables($input: VariableUpsertInput!) {
      variableUpsert(input: $input)
    }
    """
    variables = {
        "input": {
            "serviceId": SERVICE_ID,
            "environmentId": ENV_ID,
            "name": key,
            "value": value
        }
    }
    res = requests.post(url, headers=headers, json={"query": mutation, "variables": variables})
    print(f"{key}: status={res.status_code}, response={res.text[:200]}")

print("DONE")
