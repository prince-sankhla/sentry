"""SENTRY FIELD vision runtime.

Heavy CV dependencies are loaded only when the corresponding runtime is used,
so lightweight gateway routes and dispatch validation remain testable without
OpenCV/vision model packages installed.
"""

__all__ = ["FieldScanner", "run_field_scanner", "run_pothole_demo"]


def __getattr__(name: str):
    if name == "run_pothole_demo":
        from .engine import run_pothole_demo
        return run_pothole_demo
    if name in {"FieldScanner", "run_field_scanner"}:
        from .scanner import FieldScanner, run_field_scanner
        return {"FieldScanner": FieldScanner, "run_field_scanner": run_field_scanner}[name]
    raise AttributeError(name)
