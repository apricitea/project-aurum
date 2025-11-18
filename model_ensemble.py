"""Legacy import path maintained for backwards compatibility."""

from __future__ import annotations

try:  # pragma: no cover - best-effort import
    from src.domains.trading.infrastructure.ml_models.model_ensemble import (
        IDXQuantitativeModel as _IDXQuantitativeModel,
    )
except Exception:  # noqa: BLE001 - fall back to stub
    class IDXQuantitativeModel:
        """Lightweight stand-in so the API can start."""

        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def predict(self, features):
            return []
else:
    IDXQuantitativeModel = _IDXQuantitativeModel

__all__ = ["IDXQuantitativeModel"]
