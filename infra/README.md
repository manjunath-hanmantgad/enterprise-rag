# Infrastructure — Enterprise RAG

## Prerequisites
- Azure CLI (`az`)
- Bicep CLI (`az bicep install`)
- Azure subscription access

## Deploy (dev)

```bash
az group create --name enterprise-rag-dev-rg --location eastus

az deployment group create \
  --resource-group enterprise-rag-dev-rg \
  --template-file infra/bicep/main.bicep \
  --parameters infra/environments/dev.parameters.json \
  --parameters postgresAdminPassword="$(openssl rand -base64 24)"
```

## Azure AI Search
The `free` tier has 1 index limit — sufficient for dev/staging.
Switch to `basic` tier (~$75/month) for production with multiple indexes.

### Create the search index after deployment
After deploying, run:
```bash
python scripts/create_search_index.py \
  --endpoint "$(az deployment group show ... --query properties.outputs.aiSearchEndpoint.value)"
```
(You will need to create this script — it calls the Azure AI Search REST API to create the index schema.)

### Key Vault secret placeholders
Store secrets in Key Vault and inject at runtime:
- `searchAdminKey` (maps to `AZURE_AI_SEARCH_KEY`)
- `AZURE_OPENAI_KEY`
- `OPENAI_API_KEY`

Do not inline admin keys in Bicep templates.
