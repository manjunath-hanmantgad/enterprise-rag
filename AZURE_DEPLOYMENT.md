# Azure Deployment Guide — Enterprise RAG

## Prerequisites
- Azure CLI 2.50+
- Bicep CLI (`az bicep install`)
- Docker
- Access to Azure subscription/resource group
- Required secrets for OpenAI/Azure OpenAI, database, and admin token

## First-time deployment

### Step 1 — Create resource group
```bash
az login
az group create \
  --name enterprise-rag-dev-rg \
  --location eastus
```

### Step 2 — Deploy infrastructure
```bash
az deployment group create \
  --resource-group enterprise-rag-dev-rg \
  --template-file infra/bicep/main.bicep \
  --parameters infra/environments/dev.parameters.json \
  --parameters postgresAdminPassword="$(openssl rand -base64 24)"
```

Capture outputs for ACR, Key Vault, and Container App names.

### Step 3 — Build and push API image
```bash
az acr login --name <ACR_NAME>

docker build -t <ACR_LOGIN_SERVER>/enterprise-rag:latest .
docker push <ACR_LOGIN_SERVER>/enterprise-rag:latest
```

### Step 4 — Add secrets to Key Vault
```bash
az keyvault secret set \
  --vault-name <KEY_VAULT_NAME> \
  --name openai-api-key \
  --value "$OPENAI_API_KEY"

az keyvault secret set \
  --vault-name <KEY_VAULT_NAME> \
  --name admin-token \
  --value "$ADMIN_TOKEN"

az keyvault secret set \
  --vault-name <KEY_VAULT_NAME> \
  --name rag-database-url \
  --value "postgresql://<user>:<password>@<host>:5432/enterprise_rag?sslmode=require"
```

### Step 5 — Configure Container App env vars
```bash
az containerapp update \
  --name <ENTERPRISE_RAG_CONTAINER_APP> \
  --resource-group enterprise-rag-dev-rg \
  --set-env-vars \
    LLM_PROVIDER=azure \
    RAG_RETRIEVAL_PROVIDER=azure_ai_search \
    STORAGE_BACKEND=azure_postgres \
    AZURE_OPENAI_ENDPOINT=https://<your-openai-resource>.openai.azure.com/ \
    DATABASE_URL="postgresql://<user>:<password>@<host>:5432/enterprise_rag?sslmode=require"
```

### Step 6 — Verify
```bash
curl https://<ENTERPRISE_RAG_FQDN>/health
curl https://<ENTERPRISE_RAG_FQDN>/ready
```
Expected both endpoints return success payloads.

## Ongoing deployments
- Push new image tag to ACR.
- Update Container App revision.
- Run smoke checks on `/health`, `/ready`, and `/metrics/prometheus`.

## Rollback
Use revision rollback steps from `RUNBOOK.md`.
