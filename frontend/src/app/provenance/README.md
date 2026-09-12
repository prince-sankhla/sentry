# CY-03 Frontend

The provenance control room is available at `/provenance` and is exposed in the SENTRY Intelligence navigation.

The `/provenance/simulator` surface provides a deterministic demonstration of the six supported case modes: clean plus the five CY-03 mutation families.

Both surfaces consume the FastAPI provenance endpoints and never execute generated artifacts in the browser.
