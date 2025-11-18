"""Legacy import path maintained for backwards compatibility."""

from src.domains.trading.application.services.signal_generator import (
    SignalGenerator,
    AlertSystem,
)

__all__ = ["SignalGenerator", "AlertSystem"]
