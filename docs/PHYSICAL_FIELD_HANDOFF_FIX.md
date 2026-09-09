# SENTRY FIELD handoff context fix

The investigation workspace must pass the exact field tender and inspection requirement into SENTRY FIELD. The Field page intentionally refuses to start when that context is missing.

The real audit case fixtures use these field profiles:

- `delhi-cwg` → `FIELD-AUDIT-DELHI-CWG` → `REQ-AUDIT-DELHI-01`
- `dhanbad-led` → `FIELD-AUDIT-DHANBAD-LED` → `REQ-AUDIT-DHANBAD-01`

The investigation handoff now includes `case`, `tender`, and `requirement` query parameters. This supplies mission context only; the existing Field `/dispatch` contract remains responsible for validating and authorizing the exact tender, requirement, capability, and machine before a mission can run.
