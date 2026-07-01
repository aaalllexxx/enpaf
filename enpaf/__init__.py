"""
ENPAF — Engine for Native Python App Framework
Build Android APK applications using Python + HTML/CSS/JS.
"""

from importlib.metadata import version as _version, PackageNotFoundError

# Single source of truth: read the installed distribution's version (built from
# pyproject.toml). Fall back to a literal only when running from an uninstalled
# source checkout.
try:
    __version__ = _version("enpaf")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "1.1.3"

__author__ = "ENPAF Team"

from enpaf.core.app import EnpafApp

__all__ = ["EnpafApp", "__version__"]
