"""Internal plugin used by the secure plugin loader tests.

This module intentionally contains a minimal IPlugin implementation so
`InMemoryPluginLoader` can load a known-safe plugin from `src/plugins/`.
"""

from __future__ import annotations

from src.interfaces.plugin import PluginPriority, PluginType, SimplePlugin


class InternalSimplePlugin(SimplePlugin):
    def __init__(self) -> None:
        super().__init__(
            name="internal_simple",
            plugin_type=PluginType.INTEGRATION,
            version="1.0.0",
            priority=PluginPriority.NORMAL,
            capabilities=["test"],
        )

