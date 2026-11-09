# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {"name": "synapse_pyspark"},
# META   "dependencies": {"lakehouse": {
# META     "default_lakehouse": "__LAKEHOUSE_ID__",
# META     "default_lakehouse_name": "title_iq_lh",
# META     "default_lakehouse_workspace_id": "__WORKSPACE_ID__"
# META   }}
# META }

# PARAMETERS CELL ********************

pipeline_run_id = "manual"

# METADATA ********************

# META {"language":"python","language_group":"synapse_pyspark"}

# CELL ********************

from datetime import datetime, timezone

from pyspark.sql import functions as F

TABLES = [
    "property", "party", "agent_office", "title_order", "recorded_instrument", "encumbrance",
    "commitment", "policy", "rel_order_property", "rel_order_party", "rel_property_instrument",
    "rel_order_encumbrance", "rel_order_commitment", "rel_commitment_policy", "rel_order_office",
    "rel_instrument_encumbrance", "order_risk_snapshot", "daily_title_operations", "property_title_summary",
]
DATE_COLUMNS = {
    "title_order": ["opened_date", "target_close_date", "search_effective_date"],
    "recorded_instrument": ["recorded_date"], "commitment": ["issued_date"], "policy": ["issued_date"],
    "order_risk_snapshot": ["snapshot_date"], "daily_title_operations": ["operation_date"],
}

counts = {}
for table in TABLES:
    df = spark.read.parquet(f"Files/source/{table}.parquet")
    for column in DATE_COLUMNS.get(table, []):
        df = df.withColumn(column, F.col(column).cast("date"))
    df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(table)
    counts[table] = df.count()
    print(f"{table}: {counts[table]}")

log = [(pipeline_run_id, "build_curated_tables", "Succeeded", sum(counts.values()), datetime.now(timezone.utc))]
spark.createDataFrame(log, "run_id string, stage string, status string, row_count long, completed_at timestamp") \
    .write.mode("append").saveAsTable("pipeline_run_log")

# METADATA ********************

# META {"language":"python","language_group":"synapse_pyspark"}
