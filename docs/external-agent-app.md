# External Fabric Data Agent showcase

The showcase is a Python 3.13 Azure Function on Flex Consumption. Its web page lets an authenticated tenant user send a question to the Lakehouse-only Fabric Data Agent from outside Fabric and shows the measured comparison of all four published agents.

## Endpoints after deployment

- Sign-in and launch: `https://<function-app>.azurewebsites.net/.auth/login/aad?post_login_redirect_uri=/api/index`
- Anonymous health check: `https://<function-app>.azurewebsites.net/api/health`
- Tenant: `<tenant-id>`
- Entra application/client ID: `<app-client-id>`
- Application ID URI: `api://<app-client-id>`

The launch URL explicitly enters the App Service Authentication flow and returns to the UI. The Lakehouse-only agent is the enabled demo path. The Ontology-only, semantic-model-only, and hybrid benchmarks ran successfully with a user identity. The service principal can invoke all four published agents, but the current Fabric preview returns a downstream 401 when those agents query Ontology or semantic-model sources. This remained true after verifying Contributor workspace access, the Ontology/Graph/Lakehouse access chain, and an explicit semantic-model Read grant through the security group allowed to use Fabric APIs.

## Security model

- App Service Authentication requires single-tenant Microsoft Entra sign-in for the UI and `/api/ask`.
- `/api/health` is the only anonymous path and contains no data.
- The Function uses a user-assigned managed identity for Azure Storage, Application Insights, and Key Vault.
- A dedicated Entra service principal calls Fabric because the Data Agent MCP runtime does not currently support managed identity authentication.
- The MCP client requests the audience documented on the current MCP server page: `https://api.fabric.microsoft.com/.default`.
- The Fabric client secret is generated directly into Key Vault and never committed, printed, or returned to the browser.
- The service principal is in a security group that the Fabric admin settings allow to use Fabric APIs, and it has Contributor access only to this POC workspace.
- Prompt and answer bodies are deliberately excluded from application logging.

## Runtime behavior

`POST /api/ask` accepts this shape:

```json
{
  "question": "Summarize ORDER000123 and explain its risk score.",
  "agent": "direct"
}
```

`agent` is allowlisted to `direct`, `ontology`, `semantic`, or `hybrid`; the UI enables only the proven `direct` path. Questions are normalized and limited to 500 characters, the outbound MCP call has a 110-second timeout, and the browser aborts at 120 seconds.

`fabric_agent_client.py` is application integration code. It obtains a token, connects to the published Fabric MCP server, discovers the agent tool, sends the question, and returns the response. It does not implement the Data Agent: the source selection, natural-language query generation, query execution, and answer generation remain inside the published no-code Fabric item.

## Cost and operation

Flex Consumption has no always-ready instances in this POC and scales to zero. This minimizes idle application compute but permits a cold start. The Fabric F16/F32/F64 capacity is the dominant active cost and should be paused when demonstrations finish. Controlled testing selected F32 for interactive demos; it was 17.7% faster on mean latency than F16 in the eight-question sample, while F64 did not improve on F32.

The app stays deployed while the Fabric capacity is paused. Its health endpoint and sign-in continue to work, but Data Agent questions require the Fabric capacity to be resumed.

## Deployment

Infrastructure and code follow the checked-in `azure.yaml`, `infra/`, and `src/agent-demo/` definitions. Run `azd up` with your own subscription; `infra/main.bicep` derives unique resource names from the environment.
