# PII tag missing on patients.email column

- **Incident ID**: `9ce96bdd-0009-4030-b8aa-2e0a879ae78c`
- **Kind**: `glossary_gap`
- **Severity**: **HIGH**
- **Detected at**: 2026-07-28T20:09:37.559974+00:00
- **Asset**: `urn:li:dataset:(urn:li:dataPlatform:postgres,healthcare.patients,PROD)`
- **Owners**: compliance@acme.io, data-platform@acme.io
- **Domain**: Healthcare

## Summary
The `email` column on `patients` does not have the `PII` glossary term applied. This is a compliance gap — three downstream reports inherit the column without masking.

## Root cause hypothesis
The configured LLM is not available, so a heuristic root cause is reported. Inspect the raw signal: {'missing_tag': 'PII', 'column': 'email', 'expected_owners': ['compliance@acme.io']}

## Suggested fix
Re-run the upstream pipeline, then re-validate the assertion. If it persists, check the most recent schema change on the upstream dataset.

## Blast radius
- Upstream assets: 1
- Downstream assets: 2

---
*Generated automatically by [LineagePulse](https://github.com/ademidun/lineagepulse) — DataHub Agent Hackathon submission.*