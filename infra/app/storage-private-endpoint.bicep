param virtualNetworkName string
param subnetName string
param storageAccountName string
param location string = resourceGroup().location
param tags object = {}

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' existing = {
  name: virtualNetworkName
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

module privateDnsZone 'br/public:avm/res/network/private-dns-zone:0.7.1' = {
  name: 'storageBlobDns'
  params: {
    name: 'privatelink.blob.${environment().suffixes.storage}'
    location: 'global'
    tags: tags
    virtualNetworkLinks: [
      {
        name: '${storageAccountName}-blob-link'
        virtualNetworkResourceId: vnet.id
        registrationEnabled: false
        location: 'global'
        tags: tags
      }
    ]
  }
}

module privateEndpoint 'br/public:avm/res/network/private-endpoint:0.11.0' = {
  name: 'storageBlobPrivateEndpoint'
  params: {
    name: 'pe-${storageAccountName}-blob'
    location: location
    tags: tags
    subnetResourceId: '${vnet.id}/subnets/${subnetName}'
    privateLinkServiceConnections: [
      {
        name: 'blob'
        properties: {
          privateLinkServiceId: storage.id
          groupIds: ['blob']
        }
      }
    ]
    customDnsConfigs: []
    privateDnsZoneGroup: {
      name: 'blob'
      privateDnsZoneGroupConfigs: [
        {
          name: 'blob'
          privateDnsZoneResourceId: privateDnsZone.outputs.resourceId
        }
      ]
    }
  }
}
