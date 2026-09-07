# SENTRY FIELD

Physical-world verification layer for SENTRY procurement investigations.

## Hackathon/demo flow

```text
Tender → Requirement → Capability → Machine → Permission
                                      ↓
                                  Mission dispatch
                                      ↓
                                   Rover / camera
                                      ↓
                     Vision + QR/OCR + IoT telemetry
                                      ↓
                                  Evidence
                                      ↓
                         Contract vs reality
                                      ↓
                         Discrepancy / explanation
```

The field Command Center is designed so a judge can select a real government eProcurement example, select the exact inspection requirement, authorize a mission, start the rover inspection, and see live detections plus captured evidence in the same workspace.

## One-time setup

From the repository root:

```powershell
python sentry_field/scripts/bootstrap_all.py
python sentry_field/scripts/test_vision_setup.py
python sentry_field/scripts/test_field_pipeline.py
```

`bootstrap_all.py` installs missing Python packages and downloads configured field-model weights into `models/field/`. Large weights are intentionally not committed to the web repository.

## Run the demo locally

Terminal 1 — field gateway:

```powershell
python sentry_field/scripts/run_field_api.py
```

Terminal 2 — Next.js frontend:

```powershell
cd frontend
npm ci
npm run dev
```

Open:

```text
http://localhost:3000/field
```

The frontend reads the field tender catalog from the local gateway, not from hardcoded UI state. The catalog is stored at `sentry_field/data/demo_tenders.json` and can also be seeded into the core SENTRY `tenders` database with `python scripts/seed_field_demo_tenders.py`.

## Demo tender catalog

The catalog contains verified government eProcurement examples with explicit field-demo inspection profiles for:

- street-light / CCMS maintenance
- LED street-light deployment
- CCTV physical deployment
- road + drain works
- road studs / markings
- drain covers

Real source links are retained for judge verification. Demo quantities and demo sites are explicitly labelled as field-demo profiles; they are not silently presented as source BOQ quantities.

## Gateway API

The canonical gateway is `sentry_field.api:app`.

- `GET /health` — service health
- `GET /capabilities` — capability registry exposed to clients
- `GET /tenders` — field inspection tender catalog
- `GET /tenders/{id}` — one tender profile
- `POST /dispatch` — validate and authorize a tender-scoped field mission
- `POST /telemetry` — rover battery, speed and GPS telemetry
- `GET /status` — live mission state
- `GET /events` — recent mission/evidence events
- `POST /stop` — stop and revoke the active mission
- `GET /stream` — annotated MJPEG inspection stream; requires an authorized mission
- `/evidence-files/...` — captured evidence frames served by the gateway

`api_fast.py` remains only as a compatibility import and points to the canonical gateway so the two entrypoints cannot silently drift apart.

## Current capabilities

- pothole detection
- road crack / surface distress detection
- streetlight / solar streetlight discovery
- CCTV camera discovery
- signboard / road-sign discovery
- drain / manhole-cover discovery
- barrier / guardrail / traffic-cone discovery
- solar-panel discovery
- utility-pole discovery
- asset OCR/text
- asset QR
- asset barcode when the barcode backend is available
- person-aware context filtering
- lightweight IoU tracking and evidence de-duplication
- structured field evidence with detector, confidence, bbox, timestamp, mission and requirement hooks

## Live camera

```powershell
$env:SENTRY_CAMERA_URL="http://PHONE-IP:4747/video"
python sentry_field/scripts/run_field_scanner.py
```

The Command Center uses the same camera source through the field gateway. Expensive detectors run at different frame intervals so the gateway does not need to execute every model on every frame.

## IoT integration

The rover can POST telemetry to:

```text
POST /telemetry
```

Example payload:

```json
{
  "machine_id": "ROVER-001",
  "battery": 87,
  "speed": 0.4,
  "lat": 26.9124,
  "lon": 75.7873
}
```

The gateway then exposes live GPS/battery/speed state to the Command Center. The rover implementation can use ESP32 HTTP, another local bridge, or a future MQTT/WebSocket adapter; SENTRY only relies on the stable telemetry contract.

## Evidence policy

Every detector-backed evidence event should remain tied to mission ID, requirement ID, timestamp and source frame. RGB vision is observational. It does not certify material composition, pavement thickness, concrete strength or electrical performance without appropriate specialist instrumentation.

SENTRY FIELD is an evidence and verification layer. A discrepancy is a signal for human investigation, not an automatic finding of fraud.
