param location string
param searchServiceName string
param sku string = 'basic'
param replicaCount int = 1
param partitionCount int = 1

resource searchService 'Microsoft.Search/searchServices@2023-11-01' = {
  name: searchServiceName
  location: location
  sku: {
    name: sku
  }
  properties: {
    replicaCount: replicaCount
    partitionCount: partitionCount
    publicNetworkAccess: 'enabled'
    authOptions: {
      apiKeyOnly: {}
    }
  }
}

output endpoint string = 'https://${searchServiceName}.search.windows.net'
output name string = searchService.name
