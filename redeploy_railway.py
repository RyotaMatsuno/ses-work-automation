import requests

RAILWAY_API_TOKEN = "fbc5deef-ab29-4f5c-b7b8-6dc2cc2e9c81"
SERVICE_ID = "484966c3-2d1c-4736-9f69-891f11a35128"
ENVIRONMENT_ID = "46e90371-2c0b-4108-aefa-385df6916300"

headers = {"Authorization": f"Bearer {RAILWAY_API_TOKEN}", "Content-Type": "application/json"}

query = """
mutation serviceInstanceRedeploy($serviceId: String!, $environmentId: String!) {
  serviceInstanceRedeploy(serviceId: $serviceId, environmentId: $environmentId)
}
"""

res = requests.post(
    "https://backboard.railway.app/graphql/v2",
    headers=headers,
    json={"query": query, "variables": {"serviceId": SERVICE_ID, "environmentId": ENVIRONMENT_ID}},
    timeout=30,
)
print(f"Status: {res.status_code}")
print(res.text[:300])
