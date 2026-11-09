param name string
param location string = resourceGroup().location
param tags object = {}
param applicationInsightsName string
param appServicePlanId string
param appSettings object = {}
param storageAccountName string
param deploymentStorageContainerName string
param identityId string
param identityClientId string
param entraClientId string
param tenantId string
param virtualNetworkSubnetId string
param instanceMemoryMB int = 2048
param maximumInstanceCount int = 2
param serviceName string = 'agent-demo'

var applicationInsightsIdentity = 'ClientId=${identityClientId};Authorization=AAD'
var baseAppSettings = {
  AzureWebJobsStorage__credential: 'managedidentity'
  AzureWebJobsStorage__clientId: identityClientId
  AzureWebJobsStorage__blobServiceUri: storage.properties.primaryEndpoints.blob
  APPLICATIONINSIGHTS_AUTHENTICATION_STRING: applicationInsightsIdentity
  APPLICATIONINSIGHTS_CONNECTION_STRING: applicationInsights.properties.ConnectionString
}

resource storage 'Microsoft.Storage/storageAccounts@2022-09-01' existing = {
  name: storageAccountName
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' existing = {
  name: applicationInsightsName
}

module functionApp 'br/public:avm/res/web/site:0.15.1' = {
  name: '${serviceName}-flex-consumption'
  params: {
    kind: 'functionapp,linux'
    name: name
    location: location
    tags: union(tags, { 'azd-service-name': serviceName })
    serverFarmResourceId: appServicePlanId
    managedIdentities: {
      userAssignedResourceIds: [identityId]
    }
    keyVaultAccessIdentityResourceId: identityId
    virtualNetworkSubnetId: virtualNetworkSubnetId
    functionAppConfig: {
      deployment: {
        storage: {
          type: 'blobContainer'
          value: '${storage.properties.primaryEndpoints.blob}${deploymentStorageContainerName}'
          authentication: {
            type: 'UserAssignedIdentity'
            userAssignedIdentityResourceId: identityId
          }
        }
      }
      scaleAndConcurrency: {
        instanceMemoryMB: instanceMemoryMB
        maximumInstanceCount: maximumInstanceCount
      }
      runtime: {
        name: 'python'
        version: '3.13'
      }
    }
    siteConfig: {
      alwaysOn: false
      minTlsVersion: '1.2'
      ftpsState: 'Disabled'
      http20Enabled: true
    }
    appSettingsKeyValuePairs: union(appSettings, baseAppSettings)
    authSettingV2Configuration: {
      platform: {
        enabled: true
        runtimeVersion: '~1'
      }
      globalValidation: {
        requireAuthentication: true
        unauthenticatedClientAction: 'RedirectToLoginPage'
        redirectToProvider: 'azureActiveDirectory'
        excludedPaths: ['/api/health']
      }
      identityProviders: {
        azureActiveDirectory: {
          enabled: true
          registration: {
            clientId: entraClientId
            clientSecretSettingName: 'ENTRA_CLIENT_SECRET'
            openIdIssuer: '${environment().authentication.loginEndpoint}${tenantId}/v2.0'
          }
          validation: {
            allowedAudiences: ['api://${entraClientId}']
          }
        }
      }
      login: {
        tokenStore: {
          enabled: true
        }
      }
      httpSettings: {
        requireHttps: true
        routes: {
          apiPrefix: '/.auth'
        }
        forwardProxy: {
          convention: 'Standard'
        }
      }
    }
  }
}

output SERVICE_NAME string = functionApp.outputs.name
output SERVICE_URI string = 'https://${functionApp.outputs.defaultHostname}'
