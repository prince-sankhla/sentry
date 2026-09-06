# SENTRY FIELD

Physical-world verification layer for SENTRY procurement investigations.

## Current runtime

The field stack is designed as a capability-based inspection pipeline rather than one monolithic detector:

```text
Tender → Requirement → Capability → Machine → Mission
                                      ↓
                                   Scanner
                                      ↓
                ┌─────────────────────┼─────────────────────┐
                │                     │                     │
          Specialized CV       Open-vocabulary       Identity signals
          pothole/road         public assets         QR / OCR
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

## Implemented

- Live phone/DroidCam stream input
- Latest-frame low-latency capture in the validated pothole demo
- Specialized pothole detector
- General context detector for person-aware false-positive suppression
- Open-vocabulary asset discovery using YOLO-World when its optional model is bootstrapped
- QR decoding through OpenCV
- Optional OCR through `pytesseract` when available on the machine
- IoU-based lightweight tracking/de-duplication for field evidence
- Structured evidence records with frame, timestamp, detector, confidence, bbox, track ID, mission/requirement hooks and verification state
- CPU/CUDA-compatible Ultralytics inference

## Target visual capabilities

- pothole
- road crack / surface distress
- streetlight / solar streetlight
- CCTV camera
- signboard / road sign
- drain / manhole cover
- road barrier / guardrail / traffic cone
- solar panel
- utility pole
- asset text / OCR
- asset QR / barcode

## Important accuracy rule

The general detector is an exploration and coverage layer. It must not be treated as proof of a contractual violation by itself. Specialized models, contextual filtering, repeated observation, asset identity and physical/sensor measurements are progressively stronger verification signals.

The vision layer reports observations. It does not declare legal guilt or contractor fraud.

## Running the unified scanner

Bootstrap the optional open-vocabulary model:

```powershell
python sentry_field/scripts/bootstrap_world_model.py
```

Then run:

```powershell
$env:SENTRY_CAMERA_URL="http://PHONE-IP:4747/video"
python sentry_field/scripts/run_field_scanner.py
```

Press `Q` to stop.
