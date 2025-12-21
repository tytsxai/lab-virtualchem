"""Backward-compatible shim for the experiment engine.

The canonical implementation lives in `src/core/experiment_engine/`.
Keep this module to avoid breaking existing imports.
"""

from __future__ import annotations

from .experiment_engine import ExperimentController

__all__ = ["ExperimentController"]

