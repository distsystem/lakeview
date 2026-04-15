"""Plugin registry — ordered list, first match wins."""

import pyarrow as pa

from lakeview.plugins.agent_run import AgentRunPlugin
from lakeview.plugins.base import SchemaPlugin

_PLUGINS: list[SchemaPlugin] = [
    AgentRunPlugin(),
]


def detect_plugin(schema: pa.Schema) -> SchemaPlugin | None:
    for plugin in _PLUGINS:
        if plugin.matches(schema):
            return plugin
    return None
