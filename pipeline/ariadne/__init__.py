# Written with AI assistance (Claude Code). See AI_USE.md.
"""ARIADNE build-time pipeline. Generated data files record PIPELINE_VERSION (CLAUDE.md rule 10)."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("ariadne")
except PackageNotFoundError:  # running from a source tree without installing
    __version__ = "0.0.0+unknown"

PIPELINE_VERSION = __version__
