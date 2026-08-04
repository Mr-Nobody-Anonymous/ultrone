#!/usr/bin/env python3
"""Tests for the Plugin Marketplace."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import unittest
from plugins.marketplace.installer import PluginInstaller
from plugins.marketplace.plugin_registry import PluginMarketplace

class TestPluginInstaller(unittest.TestCase):
    def test_install_uninstall(self):
        installer = PluginInstaller(plugin_dir="/tmp/test_plugins")
        self.assertTrue(installer.install("test_plugin"))
        self.assertTrue(installer.is_installed("test_plugin"))
        self.assertTrue(installer.uninstall("test_plugin"))
        self.assertFalse(installer.is_installed("test_plugin"))

class TestPluginMarketplace(unittest.TestCase):
    def test_publish_search(self):
        market = PluginMarketplace()
        market.publish("awesome_plugin", "1.0.0", "An awesome plugin")
        results = market.search("awesome")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "awesome_plugin")
    def test_download(self):
        market = PluginMarketplace()
        market.publish("test", "1.0.0")
        plugin = market.download("test")
        self.assertEqual(plugin["downloads"], 1)

if __name__ == "__main__":
    unittest.main(verbosity=2)
