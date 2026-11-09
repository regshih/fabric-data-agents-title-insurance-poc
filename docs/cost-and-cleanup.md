# Cost and cleanup

`fabrictitleiqpoc` is a dedicated F16 Azure Fabric capacity and is billable while active. It should be paused outside build, refresh, benchmark, and demo windows. The workspace and OneLake data persist while paused.

The capacity was verified in the `Paused` state on 2026-09-04 after the POC build and validation runs.

Pause/resume:

```powershell
python scripts/manage_capacity.py pause
python scripts/manage_capacity.py resume
```

To remove the POC completely, delete the Fabric workspace first, then delete the Azure capacity and resource group after confirming no other resources were added. Destructive cleanup is intentionally not automated or executed by default.
