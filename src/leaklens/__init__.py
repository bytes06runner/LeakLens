"""LeakLens: static and dynamic detection of data leakage in Python ML code."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("leaklens")
except PackageNotFoundError:  # running from a source tree without install
    __version__ = "0.0.0+unknown"

# The six leakage types defined in docs/TAXONOMY.md (Phase 1). Kept here so every stage uses one vocabulary.
LEAKAGE_TYPES: tuple[str, ...] = (
    "preprocessing",
    "overlap",
    "multi_test",
    "group",
    "temporal",
    "target_derived",
)

__all__ = ["LEAKAGE_TYPES", "__version__"]
