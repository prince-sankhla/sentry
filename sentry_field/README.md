# SENTRY FIELD

Physical-world verification layer for SENTRY procurement investigations.

## Purpose

SENTRY FIELD connects contract requirements to field inspection capabilities and returns structured observations/evidence to the main SENTRY platform.

This module is deliberately isolated from the existing Next.js application so the web platform and local computer-vision runtime can evolve independently.

## Current implementation

- Live phone/DroidCam stream input
- Latest-frame capture to minimize latency
- Ultralytics inference runtime
- Current validated pothole detector
- Configurable inference size, confidence threshold, and frame stride
- CPU/CUDA device selection

## Planned capability modules

- pothole
- road distress / cracks
- streetlight
- CCTV
- signboard
- OCR
- QR/barcode
- GPS/telemetry
- evidence packaging

## Architecture

Tender → Requirement → Capability → Machine → Mission → Observation → Evidence → Contract-vs-Reality comparison

The vision layer reports observations. It must not declare legal guilt or contractor fraud by itself.
