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

KEYS = {
    "property":"property_id", "party":"party_id", "agent_office":"office_id", "title_order":"order_id",
    "recorded_instrument":"instrument_id", "encumbrance":"encumbrance_id", "commitment":"commitment_id", "policy":"policy_id",
}
RELATIONSHIPS = {
    "rel_order_property": (("order_id","title_order","order_id"),("property_id","property","property_id")),
    "rel_order_party": (("order_id","title_order","order_id"),("party_id","party","party_id")),
    "rel_property_instrument": (("property_id","property","property_id"),("instrument_id","recorded_instrument","instrument_id")),
    "rel_order_encumbrance": (("order_id","title_order","order_id"),("encumbrance_id","encumbrance","encumbrance_id")),
    "rel_order_commitment": (("order_id","title_order","order_id"),("commitment_id","commitment","commitment_id")),
    "rel_commitment_policy": (("commitment_id","commitment","commitment_id"),("policy_id","policy","policy_id")),
    "rel_order_office": (("office_id","agent_office","office_id"),("order_id","title_order","order_id")),
    "rel_instrument_encumbrance": (("instrument_id","recorded_instrument","instrument_id"),("encumbrance_id","encumbrance","encumbrance_id")),
}

results = []
now = datetime.now(timezone.utc)
for table, key in KEYS.items():
    df = spark.table(table)
    invalid = df.filter(F.col(key).isNull()).count() + (df.count() - df.select(key).distinct().count())
    results.append((pipeline_run_id, table, "non_null_unique_key", 0, invalid, "Passed" if invalid == 0 else "Failed", now, ""))
for table, endpoints in RELATIONSHIPS.items():
    rel = spark.table(table)
    invalid = 0
    for column, entity_table, entity_key in endpoints:
        entity = spark.table(entity_table).select(entity_key)
        invalid += rel.join(entity, rel[column] == entity[entity_key], "left_anti").count()
    results.append((pipeline_run_id, table, "relationship_endpoints_exist", 0, invalid, "Passed" if invalid == 0 else "Failed", now, ""))

risk_invalid = spark.table("order_risk_snapshot").filter("risk_score < 0 OR risk_score > 100").count()
results.append((pipeline_run_id, "order_risk_snapshot", "risk_score_range", 0, risk_invalid, "Passed" if risk_invalid == 0 else "Failed", now, ""))
spark.createDataFrame(results, "run_id string, table_name string, check_name string, expected long, actual long, status string, checked_at timestamp, notes string") \
    .write.mode("overwrite").saveAsTable("data_quality_result")
if any(row[4] for row in results):
    raise RuntimeError("data quality checks failed; see data_quality_result")

# METADATA ********************

# META {"language":"python","language_group":"synapse_pyspark"}
