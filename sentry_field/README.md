# SENTRY FIELD

Physical-world verification layer for SENTRY procurement investigations.

## Architecture

```text
Tender → Requirement → Capability → Machine → Mission
                                      ↓
                                   Scanner
                                      ↓
                ┌─────────────────────┼─────────────────────┐
                │                     │                     │
          Specialized CV       Open-vocabulary       Identity signals
          pothole/crack        public assets          QR / OCR / barcode
                │                     │                     │
                └─────────────────────┼─────────────────────┘
                                      ↓
                              Context + filtering
                                      ↓
                          Tracking + de-duplication
                                      ↓
                                  Evidence
                                      ↓
                         Contract-vs-reality layer
```

## One-command field setup

From the repository root:

```powershell
python sentry_field/scripts/bootstrap_all.py
python sentry_field/scripts/test_vision_setup.py
```

`bootstrap_all.py` installs missing Python packages and downloads the configured field-model weights into `models/field/`. Large weights are intentionally not committed to the web repository. The setup checker loads every configured model and reports optional third-party model failures separately.

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

## Live scanner

```powershell
$env:SENTRY_CAMERA_URL="http://PHONE-IP:4747/video"
python sentry_field/scripts/run_field_scanner.py
```

The scanner can use one camera feed for multiple capabilities. It should schedule expensive detectors at different frame intervals rather than running every model on every frame.

## Model policy

The open-vocabulary detector is a coverage/exploration layer and is not, by itself, proof of a contractual violation. Critical asset verification should combine specialized detection, context, repeated observation, identity, GPS and/or physical measurements.

Some public Hugging Face model repositories may require a user to accept repository access terms. The bootstrap script reports such a model as an optional warning instead of silently pretending it was installed.

## Accuracy rule

SENTRY FIELD reports observations and evidence. It does not declare legal guilt or contractor fraud from a detector score alone.
