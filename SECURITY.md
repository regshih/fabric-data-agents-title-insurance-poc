# Security

## Reporting a vulnerability

Please report vulnerabilities privately through GitHub's **Report a vulnerability** button on the
Security tab. Do not open a public issue that contains credentials, Azure or Fabric identifiers, logs,
or deployment output. Include a minimal reproduction with every environment value replaced by a
placeholder.

## Supported scope

This is a reference proof of concept, not a managed service. Fixes are applied to the default branch
only. Review role scope, network access, capacity schedules, and data handling before reusing any part
of it in production.

## Secrets and environment data

- No credentials are stored in the repository. Local runs use Azure CLI sign-in or
  `DefaultAzureCredential`.
- The optional external app uses a user-assigned managed identity for Storage, Application Insights,
  and Key Vault. Its Fabric service-principal secret is generated directly into Key Vault and never
  committed, printed, or returned to the browser.
- Real subscription, tenant, and resource values belong only in the ignored `.env` file.
- All data is synthetic.

Before pushing, run:

```powershell
python scripts/scan_secrets.py --history
```

It fails on keys, tokens, tenant or subscription IDs, live hostnames, and local user paths. It
supplements, but does not replace, GitHub secret scanning and push protection.
