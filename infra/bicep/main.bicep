targetScope = 'resourceGroup'

param location string = resourceGroup().location
param appName string = 'enterprise-rag'
param environment string = 'dev'
param acrImageTag string = 'latest'
param aiSearchSku string = 'free'

@secure()
param postgresAdminPassword string

var suffix = '${appName}-${environment}'
var acrName = take(replace('${suffix}acr', '-', ''), 50)
var logAnalyticsSharedKey = listKeys(resourceId('Microsoft.OperationalInsights/workspaces', '${suffix}-law'), '2020-08-01').primarySharedKey
var commonEnv = [
  {
    name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
    value: appInsights.outputs.connectionString
  }
  {
    name: 'LLM_PROVIDER'
    value: 'azure'
  }
  {
    name: 'DATABASE_URL'
    value: 'postgresql+psycopg://observatoryadmin:${postgresAdminPassword}@${postgres.outputs.fqdn}:5432/enterprise_rag'
  }
  {
    name: 'AZURE_AI_SEARCH_ENDPOINT'
    value: aiSearch.outputs.endpoint
  }
  {
    name: 'AZURE_AI_SEARCH_INDEX'
    value: 'enterprise-rag-docs'
  }
  {
    name: 'RAG_RETRIEVAL_PROVIDER'
    value: 'azure_ai_search'
  }
  {
    name: 'STORAGE_BACKEND'
    value: 'postgres'
  }
  {
    name: 'AUTH_PROVIDER'
    value: 'local'
  }
]

module acr 'modules/acr.bicep' = {
  name: 'acr'
  params: {
    location: location
    acrName: acrName
  }
}

module appInsights 'modules/appinsights.bicep' = {
  name: 'appinsights'
  params: {
    location: location
    appInsightsName: '${suffix}-ai'
    workspaceName: '${suffix}-law'
  }
}

module postgres 'modules/postgres.bicep' = {
  name: 'postgres'
  params: {
    location: location
    serverName: '${suffix}-pg'
    adminPassword: postgresAdminPassword
  }
}

module aiSearch 'modules/ai-search.bicep' = {
  name: 'ai-search'
  params: {
    location: location
    searchServiceName: take(replace('${suffix}-search', '-', ''), 60)
    sku: aiSearchSku
  }
}

module acaEnv 'modules/aca-environment.bicep' = {
  name: 'aca-env'
  params: {
    location: location
    environmentName: '${suffix}-env'
    logAnalyticsWorkspaceId: appInsights.outputs.workspaceId
    logAnalyticsSharedKey: logAnalyticsSharedKey
  }
}

module api 'modules/aca-app.bicep' = {
  name: 'api'
  params: {
    location: location
    appName: '${suffix}-api'
    environmentId: acaEnv.outputs.id
    imageName: '${acr.outputs.loginServer}/enterprise-rag:${acrImageTag}'
    containerPort: 8000
    command: [
      'uvicorn'
      'enterprise_rag.api:app'
      '--host'
      '0.0.0.0'
      '--port'
      '8000'
    ]
    env: commonEnv
  }
}

module dashboard 'modules/aca-app.bicep' = {
  name: 'dashboard'
  params: {
    location: location
    appName: '${suffix}-dashboard'
    environmentId: acaEnv.outputs.id
    imageName: '${acr.outputs.loginServer}/enterprise-rag:${acrImageTag}'
    containerPort: 8511
    command: [
      'streamlit'
      'run'
      'dashboard/app.py'
      '--server.address'
      '0.0.0.0'
      '--server.port'
      '8511'
    ]
    env: concat(commonEnv, [
      {
        name: 'DASHBOARD_API_URL'
        value: 'http://${api.outputs.fqdn}'
      }
    ])
  }
}

module keyvault 'modules/keyvault.bicep' = {
  name: 'keyvault'
  params: {
    location: location
    keyVaultName: '${suffix}-kv'
    managedIdentityPrincipalId: api.outputs.principalId
  }
}

output apiUrl string = 'https://${api.outputs.fqdn}'
output dashboardUrl string = 'https://${dashboard.outputs.fqdn}'
output aiSearchEndpoint string = aiSearch.outputs.endpoint
output keyVaultUri string = keyvault.outputs.uri
