from .test_case import TestCase
from infi.unittest.parameters import iterate
from os import path

class ConsoleScriptsTestCase(TestCase):
    def test_add_and_remove_a_valid_entry_point(self):
        from infi.projector.plugins.builtins.console_scripts import ConsoleScriptsPlugin
        plugin = ConsoleScriptsPlugin()
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            with open(path.join("src", "a", "b", "c", "__init__.py"), 'a') as fd:
                      fd.write("\ndef foo():\n    pass\n")
            self.assertFalse('foo' in plugin.get_set().get().keys())
            self.projector("console-scripts add foo a.b.c:foo")
            self.assertTrue('foo' in plugin.get_set().get().keys())
            self.projector("console-scripts remove foo")
            self.assertFalse('foo' in plugin.get_set().get().keys())

    def test_list(self):
        from infi.projector.plugins.builtins.console_scripts import ConsoleScriptsPlugin
        from mock import patch, Mock
        with patch("pprint.pprint") as pprint, patch.object(ConsoleScriptsPlugin, "get_set") as get_set:
            console_scripts = dict()
            get_set.return_value.get.return_value = console_scripts
            def side_effect(*args, **kwargs):
                called_console_scripts, = args
                self.assertEquals(console_scripts, called_console_scripts)
            pprint.side_effect = side_effect
            with self.temporary_directory_context():
                self.projector("repository init a.b.c none short long")
                self.projector("console-scripts list")
                self.assertTrue(pprint.called)
