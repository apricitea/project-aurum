"""
Compatibility shim for the removed stdlib `distutils` package.

Many third-party libraries still import `distutils.*`. Starting with
Python 3.12 the package was deleted, but `setuptools` bundles a
fully-compatible copy under `setuptools._distutils`.  This shim makes
`import distutils` resolve to that vendored implementation so existing
dependencies keep working without forcing system-wide installs.
"""

from __future__ import annotations

import sys

from setuptools import _distutils as _setuptools_distutils

# Expose the vendored package as `distutils`
sys.modules[__name__] = _setuptools_distutils
