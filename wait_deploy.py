import time

import requests

TOKEN = "fbc5deef-ab29-4f5c-b7b8-6dc2cc2e9c81"
SERVICE_ID = "484966c3-2d1c-4736-9f69-891f11a35128"
ENV_ID = "46e90371-2c0b-4108-aefa-385df6916300"

headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
url = "https://backboard.railway.app/graphql/v2"

query = """
query($serviceId: String!, $environmentId: String!) {
  deployments(input: {serviceId: $serviceId, environmentId: $environmentId}) {
    edges {
      node { id status createdAt }
    }
  }
}
"""

for i in range(12):
    res = requests.post(
        url, headers=headers, json={"query": query, "variables": {"serviceId": SERVICE_ID, "environmentId": ENV_ID}}
    )
    edges = res.json().get("data", {}).get("deployments", {}).get("edges", [])
    if edges:
        latest = edges[0]["node"]
        print(f"[{i * 10}s] status={latest['status']} id={latest['id'][:8]}")
        if latest["status"] in ("SUCCESS", "FAILED", "CRASHED"):
            break
    time.sleep(10)

print("Final check done.")
