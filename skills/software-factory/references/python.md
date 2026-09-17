# Python and PySpark profile

Pin Python and dependencies; require lint, typing, unit/integration tests, coverage, dependency/license scans, container build, SBOM, and health checks. For PySpark, verify exact Spark/Python/JVM/Iceberg/AWS Glue or EMR compatibility, distributed semantics, skew/shuffle risks, timezones/decimals/nulls, idempotency, late data, and representative integration data. Local Spark tests never prove AWS runtime compatibility.

For Iceberg, verify catalog authority, writer/readers, format version, schema/partition evolution, deterministic MERGE source uniqueness, concurrent commit retry, snapshot retention, compaction, orphan cleanup, reconciliation, and recovery. Human approval is required for destructive migration or retention changes.

