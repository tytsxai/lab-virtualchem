"""兼容层: 将 ChemLab 的 TemplateConverter 暴露为 src.converters.template_converter."""

from __future__ import annotations

from tools.chemlab_integration.src.converters.template_converter import (
    TemplateConverter,  # noqa: F401
)

__all__ = ["TemplateConverter"]
