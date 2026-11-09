targetScope = 'resourceGroup'

@minLength(1)
@maxLength(64)
param environmentName string

@allowed(['westus3'])
@metadata({ azd: { type: 'location' } })
param location string

param keyVaultOfficerPrincipalId string
param entraClientId string
param fabricWorkspaceId string
param fabricDirectAgentId string
param fabricOntologyAgentId string
param fabricSemanticAgentId string
param fabricHybridAgentId string

var abbrs = loadJsonContent('./abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var tags = {
  'azd-env-name': environmentName
  purpose: 'fabric-title-iq-agent-demo'
  data: 'synthetic'
}
var functionAppName = 'func-title-iq-agent-${resourceToken}'
var storageAccountName = 'sttitleiq${take(resourceToken, 12)}'
var keyVaultName = 'kv-titleiq-${take(resourceToken, 10)}'
var virtualNetworkName = 'vnet-title-iq-agent-${resourceToken}'
var deploymentStorageContainerName = 'app-package-${take(resourceToken, 7)}'

module functionIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.4.1' = {
  name: 'functionIdentity'
  params: {
    location: location
    tags: tags
    name: '${abbrs.managedIdentityUserAssignedIdentities}title-iq-agent-${resourceToken}'
  }
}

module appServicePlan 'br/public:avm/res/web/serverfarm:0.1.1' = {
  name: 'appServicePlan'
  params: {
    name: '${abbrs.webServerFarms}title-iq-agent-${resourceToken}'
    sku: {
      name: 'FC1'
      tier: 'FlexConsumption'
    }
    reserved: true
    location: location
    tags: tags
  }
}

module storage 'br/public:avm/res/storage/storage-account:0.8.3' = {
  name: 'storage'
  params: {
    name: storageAccountName
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    publicNetworkAccess: 'Disabled'
    networkAcls: { defaultAction: 'Deny', bypass: 'None' }
    blobServices: {
      containers: [{ name: deploymentStorageContainerName }]
    }
    minimumTlsVersion: 'TLS1_2'
    location: location
    tags: tags
  }
}

module logAnalytics 'br/public:avm/res/operational-insights/workspace:0.7.0' = {
  name: 'logAnalytics'
  params: {
    name: '${abbrs.operationalInsightsWorkspaces}title-iq-agent-${resourceToken}'
    location: location
    tags: tags
    dataRetention: 30
  }
}

module monitoring 'br/public:avm/res/insights/component:0.4.1' = {
  name: 'applicationInsights'
  params: {
    name: '${abbrs.insightsComponents}title-iq-agent-${resourceToken}'
    location: location
    tags: tags
    workspaceResourceId: logAnalytics.outputs.resourceId
    disableLocalAuth: true
  }
}

module keyVault 'app/keyvault.bicep' = {
  name: 'keyVault'
  params: {
    name: keyVaultName
    location: location
    tags: tags
    managedIdentityPrincipalId: functionIdentity.outputs.principalId
    keyVaultOfficerPrincipalId: keyVaultOfficerPrincipalId
  }
}

module virtualNetwork 'app/vnet.bicep' = {
  name: 'virtualNetwork'
  params: {
    vNetName: virtualNetworkName
    location: location
    tags: tags
  }
}

module storagePrivateEndpoint 'app/storage-private-endpoint.bicep' = {
  name: 'storagePrivateEndpoint'
  params: {
    virtualNetworkName: virtualNetwork.outputs.name
    subnetName: virtualNetwork.outputs.privateEndpointSubnetName
    storageAccountName: storage.outputs.name
    location: location
    tags: tags
  }
}

module keyVaultPrivateEndpoint 'app/keyvault-private-endpoint.bicep' = {
  name: 'keyVaultPrivateEndpoint'
  params: {
    virtualNetworkName: virtualNetwork.outputs.name
    subnetName: virtualNetwork.outputs.privateEndpointSubnetName
    keyVaultName: keyVault.outputs.name
    location: location
    tags: tags
  }
}

module rbac 'app/rbac.bicep' = {
  name: 'applicationRbac'
  params: {
    storageAccountName: storage.outputs.name
    appInsightsName: monitoring.outputs.name
    managedIdentityPrincipalId: functionIdentity.outputs.principalId
  }
}

module api 'app/api.bicep' = {
  name: 'agentDemo'
  dependsOn: [rbac]
  params: {
    name: functionAppName
    location: location
    tags: tags
    applicationInsightsName: monitoring.outputs.name
    appServicePlanId: appServicePlan.outputs.resourceId
    storageAccountName: storage.outputs.name
    deploymentStorageContainerName: deploymentStorageContainerName
    identityId: functionIdentity.outputs.resourceId
    identityClientId: functionIdentity.outputs.clientId
    entraClientId: entraClientId
    tenantId: tenant().tenantId
    virtualNetworkSubnetId: virtualNetwork.outputs.functionSubnetId
    appSettings: {
      ENTRA_CLIENT_SECRET: '@Microsoft.KeyVault(VaultName=${keyVault.outputs.name};SecretName=fabric-client-secret)'
      FABRIC_TENANT_ID: tenant().tenantId
      FABRIC_CLIENT_ID: entraClientId
      FABRIC_CLIENT_SECRET_NAME: 'fabric-client-secret'
      FABRIC_WORKSPACE_ID: fabricWorkspaceId
      FABRIC_DIRECT_AGENT_ID: fabricDirectAgentId
      FABRIC_ONTOLOGY_AGENT_ID: fabricOntologyAgentId
      FABRIC_SEMANTIC_AGENT_ID: fabricSemanticAgentId
      FABRIC_HYBRID_AGENT_ID: fabricHybridAgentId
      KEY_VAULT_URL: keyVault.outputs.uri
      MANAGED_IDENTITY_CLIENT_ID: functionIdentity.outputs.clientId
    }
  }
}

output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output KEY_VAULT_NAME string = keyVault.outputs.name
output FUNCTION_IDENTITY_NAME string = functionIdentity.outputs.name
output SERVICE_AGENT_DEMO_NAME string = api.outputs.SERVICE_NAME
output SERVICE_AGENT_DEMO_URI string = api.outputs.SERVICE_URI
