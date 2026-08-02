"""Tests for the plugin SDK."""

import pytest

from plugin_sdk.base import Plugin, PluginType, PluginContext
from plugin_sdk.discovery import PluginDiscovery
from plugin_sdk.capabilities import PluginCapabilities, Capability


class SampleAlgorithmPlugin(Plugin):
    def __init__(self):
        super().__init__(
            name="Test Algorithm",
            version="1.0.0",
            plugin_type=PluginType.ALGORITHM,
            description="A test algorithm plugin",
        )

    def execute(self, *args, **kwargs):
        input_data = kwargs.get("input_data", [])
        return {"status": "ok", "result": sum(input_data)}


class TestPlugin:
    def test_plugin_creation(self):
        plugin = SampleAlgorithmPlugin()
        assert plugin.active is False
        assert plugin.initialized is False
        assert plugin.plugin_type == PluginType.ALGORITHM

    def test_plugin_lifecycle(self):
        plugin = SampleAlgorithmPlugin()
        context = PluginContext()
        plugin.initialize(context)
        assert plugin.initialized is True
        plugin.activate()
        assert plugin.active is True
        plugin.deactivate()
        assert plugin.active is False

    def test_plugin_metadata(self):
        plugin = SampleAlgorithmPlugin()
        metadata = plugin.get_metadata()
        assert metadata["name"] == "Test Algorithm"
        assert metadata["type"] == "algorithm"

    def test_plugin_execute(self):
        plugin = SampleAlgorithmPlugin()
        result = plugin.execute(input_data=[1, 2, 3])
        assert result["status"] == "ok"


class TestPluginCapabilities:
    def test_default_capabilities(self):
        plugin = SampleAlgorithmPlugin()
        caps = PluginCapabilities(plugin)
        assert "training" in caps.get_capabilities()
        assert "inference" in caps.get_capabilities()

    def test_add_capability(self):
        plugin = SampleAlgorithmPlugin()
        caps = PluginCapabilities(plugin)
        caps.add_capability(Capability.SEARCH)
        assert "search" in caps.get_capabilities()

    def test_validation(self):
        plugin = SampleAlgorithmPlugin()
        caps = PluginCapabilities(plugin)
        issues = caps.validate()
        assert issues == []  # Algorithm type has all required capabilities
