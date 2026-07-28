# Freshness violation on taxi_trips (3h 12m stale)

- **Incident ID**: `ce0651f3-0d77-447a-a9d4-65dc46bd2c74`
- **Kind**: `freshness_violation`
- **Severity**: **CRITICAL**
- **Detected at**: 2026-07-28T20:09:33.613325+00:00
- **Asset**: `urn:li:dataset:(urn:li:dataPlatform:snowflake,demo.warehouse.taxi_trips,PROD)`
- **Owners**: ademidun@acme.io, data-platform@acme.io
- **Domain**: Mobility

## Summary
taxi_trips has not received new rows in 3h 12m. The freshness assertion expects rows at most 1h apart. Downstream ML model demand_forecaster is now training on stale data.

## Root cause hypothesis
The configured LLM is not available, so a heuristic root cause is reported. Inspect the raw signal: {'assertion_urn': 'urn:li:assertion:taxi-freshness', 'expected_max_age_minutes': 60, 'observed_age_minutes': 192}

## Suggested fix
Re-run the upstream pipeline, then re-validate the assertion. If it persists, check the most recent schema change on the upstream dataset.

## Blast radius
- Upstream assets: 1
- Downstream assets: 1
- ML models affected: urn:li:mlModel:(urn:li:dataPlatform:mlflow,demand_forecaster,PROD)
- Dashboards affected: urn:li:dashboard:(urn:li:dataPlatform:looker,daily_ops,PROD)
- Pipelines affected: urn:li:dataJob:(urn:li:dataPlatform:airflow,taxi_ingest,taxi_load)

---
*Generated automatically by [LineagePulse](https://github.com/ademidun/lineagepulse) — DataHub Agent Hackathon submission.*