# Capacity and performance decision

The subscription had active F2 capacities and paused F2/F4 capacities, all attached to existing POCs. A trial FTL64 capacity was also active, but current Data Agent prerequisites specify a paid F2+ capacity. Reusing existing capacities would introduce unrelated workload contention and/or affect other POCs.

Decision: create dedicated `fabrictitleiqpoc` in `rg-fabric-iq-title-poc-westus3`, start at F16, and pause it when idle. This matches the requested clean baseline while avoiding an unsupported assumption about trial capacity.

No F32/F64 test is justified until a published agent benchmark and Capacity Metrics show saturation, throttling, or source/Graph delay. An agent orchestration/LLM bottleneck is not expected to improve merely by scaling Fabric compute.

Commands:

```powershell
python scripts/manage_capacity.py status
python scripts/manage_capacity.py resume
python scripts/manage_capacity.py resize --sku F32
python scripts/manage_capacity.py resize --sku F16
python scripts/manage_capacity.py pause
```

The resize guard rejects SKUs above F64. The capacity remains a billable Azure resource whenever active.

