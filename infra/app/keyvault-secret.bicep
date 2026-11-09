targetScope = 'resourceGroup'

param keyVaultName string
param secretName string
@secure()
param secretValue string
param expirationUtc string = dateTimeAdd(utcNow(), 'P365D')

resource keyVault 'Microsoft.KeyVault/vaults@2025-05-01' existing = {
  name: keyVaultName
}

resource secret 'Microsoft.KeyVault/vaults/secrets@2025-05-01' = {
  parent: keyVault
  name: secretName
  properties: {
    value: secretValue
    attributes: {
      enabled: true
      exp: dateTimeToEpoch(expirationUtc)
    }
  }
}
