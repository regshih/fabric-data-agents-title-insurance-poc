param virtualNetworkName string
param subnetName string
param keyVaultName string
param location string = resourceGroup().location
param tags object = {}

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' existing = {
  name: virtualNetworkName
}

resource keyVault 'Microsoft.KeyVault/vaults@2025-05-01' existing = {
  name: keyVaultName
}

module privateDnsZone 'br/public:avm/res/network/private-dns-zone:0.7.1' = {
  name: 'keyVaultDns'
  params: {
    name: 'privatelink.vaultcore.azure.net'
    location: 'global'
    tags: tags
    virtualNetworkLinks: [
      {
        name: '${keyVaultName}-vault-link'
        virtualNetworkResourceId: vnet.id
        registrationEnabled: false
        location: 'global'
        tags: tags
      }
    ]
  }
}

module privateEndpoint 'br/public:avm/res/network/private-endpoint:0.11.0' = {
  name: 'keyVaultPrivateEndpointResource'
  params: {
    name: 'pe-${keyVaultName}'
    location: location
    tags: tags
    subnetResourceId: '${vnet.id}/subnets/${subnetName}'
    privateLinkServiceConnections: [
      {
        name: 'vault'
        properties: {
          privateLinkServiceId: keyVault.id
          groupIds: ['vault']
        }
      }
    ]
    customDnsConfigs: []
    privateDnsZoneGroup: {
      name: 'vault'
      privateDnsZoneGroupConfigs: [
        {
          name: 'vault'
          privateDnsZoneResourceId: privateDnsZone.outputs.resourceId
        }
      ]
    }
  }
}
