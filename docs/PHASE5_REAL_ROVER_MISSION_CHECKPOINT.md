# SENTRY — Phase 5 Real Rover Mission Checkpoint

**Phase:** 5 — Real Rover Mission / IoT Telemetry  
**Status:** Implementation complete; physical hardware validation remains device-dependent  
**Repository:** `prince-sankhla/sentry`  
**Branch:** `phase-5-real-rover-mission`

## Delivered

### 1. Hardware-facing rover telemetry contract
The canonical SENTRY FIELD gateway already exposes `POST /telemetry` for rover machine ID, battery, speed and optional GPS coordinates. The Phase 5 test suite now verifies the complete dispatch → rover telemetry → live status → stop lifecycle.

### 2. ESP32 reference client
`sentry_field/esp32/sentry_rover_telemetry.ino` provides a real ESP32 Wi-Fi client using the canonical gateway endpoint. It supports TinyGPSPlus input, a battery ADC integration point and a wheel-encoder speed integration point. It sends GPS only when the GPS module reports a valid fix; no synthetic coordinates are generated.

### 3. End-to-end contract coverage
`test_phase5_real_rover.py` verifies:

- exact mission dispatch
- rover telemetry with battery, speed and GPS
- mission/requirement/tender linkage visible in gateway state
- recent telemetry event creation
- telemetry with battery/speed while GPS is unavailable
- mission stop revocation
- canonical `api_fast` compatibility alias

### 4. Regression CI
The Phase 5 workflow runs the Phase 3 gateway tests, Phase 4 mobile-GPS tests, Phase 5 rover tests, the field pipeline smoke test, and the production frontend build.

## Physical validation boundary

CI cannot physically power an ESP32, connect it to the operator Wi-Fi, read the GPS module, or validate the battery/encoder wiring. Physical acceptance therefore requires the actual rover hardware and the local SENTRY FIELD gateway. The reference client is deliberately explicit about hardware calibration points and does not claim those measurements are validated by CI.

## Scope boundary

Expected-vs-observed procurement discrepancy reasoning, persistent cross-mission case aggregation, AI investigation, and final case closure remain later phases.
