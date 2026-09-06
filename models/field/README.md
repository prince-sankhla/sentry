# SENTRY FIELD model storage

Local-only model weights belong under this directory.

Recommended structure:

```text
models/field/
├── pothole/
│   └── yolo26_best.pt
├── road_distress/
│   └── best.pt
├── streetlight/
├── cctv/
├── signboard/
└── qr/
```

Do not commit large binary weights to the main web repository unless there is a deliberate release/LFS decision. The local bootstrap scripts download and validate weights instead.
