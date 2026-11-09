param vNetName string
param location string = resourceGroup().location
param privateEndpointSubnetName string = 'private-endpoints'
param functionSubnetName string = 'functions'
param tags object = {}

module virtualNetwork 'br/public:avm/res/network/virtual-network:0.6.1' = {
  name: 'vnet'
  params: {
    name: vNetName
    addressPrefixes: ['10.42.0.0/16']
    location: location
    tags: tags
    subnets: [
      {
        name: privateEndpointSubnetName
        addressPrefix: '10.42.1.0/24'
        privateEndpointNetworkPolicies: 'Disabled'
      }
      {
        name: functionSubnetName
        addressPrefix: '10.42.2.0/24'
        privateEndpointNetworkPolicies: 'Disabled'
        delegation: 'Microsoft.App/environments'
      }
    ]
  }
}

output name string = virtualNetwork.outputs.name
output privateEndpointSubnetName string = privateEndpointSubnetName
output functionSubnetId string = '${virtualNetwork.outputs.resourceId}/subnets/${functionSubnetName}'
