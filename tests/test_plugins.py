from infi import unittest
from infi.projector import plugins

class TestCase(unittest.TestCase):
    def test_invalid_plugin(self):
        class BadPlugin(plugins.CommandPlugin):
            pass
        class NotA_Plugin(object):
            pass
        self.assertFalse(plugins.plugin_repository.validate_plugin(BadPlugin))
        self.assertFalse(plugins.plugin_repository.validate_plugin(NotA_Plugin))
