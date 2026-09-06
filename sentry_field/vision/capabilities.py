from dataclasses import dataclass


@dataclass(frozen=True)
class CapabilitySpec:
    name: str
    description: str
    evidence_kind: str
    preferred_detector: str


CAPABILITIES: tuple[CapabilitySpec, ...] = (
    CapabilitySpec("pothole", "Detect visible road potholes.", "road_defect", "specialized"),
    CapabilitySpec("road_crack", "Discover visible road cracks and surface distress.", "road_defect", "open_vocabulary_or_specialized"),
    CapabilitySpec("streetlight", "Detect visible streetlights and solar streetlights.", "asset", "open_vocabulary"),
    CapabilitySpec("cctv_camera", "Detect visible CCTV/security cameras.", "asset", "open_vocabulary"),
    CapabilitySpec("signboard", "Detect visible road/public signboards.", "asset", "open_vocabulary"),
    CapabilitySpec("road_barrier", "Detect barriers, guardrails, cones and related roadside controls.", "asset", "open_vocabulary"),
    CapabilitySpec("drain", "Detect visible roadside drains and drainage covers.", "asset", "open_vocabulary"),
    CapabilitySpec("solar_panel", "Detect visible solar panels associated with public assets.", "asset", "open_vocabulary"),
    CapabilitySpec("manhole_cover", "Detect visible manhole/drain covers.", "asset", "open_vocabulary"),
    CapabilitySpec("asset_text", "Read visible asset numbers or labels.", "identity", "ocr"),
    CapabilitySpec("asset_qr", "Decode visible QR codes or asset codes.", "identity", "qr"),
    CapabilitySpec("asset_barcode", "Decode visible 1D barcodes when a barcode backend is installed.", "identity", "barcode"),
)

CAPABILITY_NAMES = tuple(item.name for item in CAPABILITIES)

# Only these classes should become field evidence from the general scene detector.
WORLD_EVIDENCE_CLASSES = {
    "streetlight",
    "solar streetlight",
    "cctv camera",
    "road sign",
    "signboard",
    "road barrier",
    "drain",
    "manhole cover",
    "solar panel",
    "traffic cone",
    "guardrail",
    "utility pole",
    "road crack",
}

# Context-only classes help suppress obvious false positives but are not field findings.
CONTEXT_CLASSES = {"person", "car", "motorcycle", "bus", "truck", "bicycle"}
