"""
Compatibility shim mapping the deprecated `aioredis` API to
`redis.asyncio`.

The upstream `aioredis` package is unmaintained and incompatible with
Python 3.12+.  Our code only needs `from_url` plus the standard Redis
client classes, all of which are available in `redis.asyncio`.  This
module re-exports them so we can keep the existing imports without
dragging in the broken dependency.
"""

from __future__ import annotations

import sys
from types import ModuleType

from redis import asyncio as _redis_asyncio


class _AioredisShim(ModuleType):
    """Proxy attribute access to redis.asyncio."""

    def __getattr__(self, item: str):
        try:
            return getattr(_redis_asyncio, item)
        except AttributeError as exc:  # pragma: no cover - fail fast
            raise AttributeError(f"aioredis shim has no attribute {item}") from exc


_shim = _AioredisShim("aioredis")
_shim.__dict__.update(
    {
        "Redis": _redis_asyncio.Redis,
        "StrictRedis": _redis_asyncio.Redis,
        "from_url": _redis_asyncio.from_url,
    }
)
sys.modules[__name__] = _shim
