from .test_case import TestCase
from infi.unittest.parameters import iterate
from os import path

class GuiScriptsTestCase(TestCase):
    def test_add_and_remove_a_valid_entry_point(self):
        from infi.projector.plugins.builtins.gui_scripts import GuiScriptsPlugin
        plugin = GuiScriptsPlugin()
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            with open(path.join("src", "a", "b", "c", "__init__.py"), 'a') as fd:
                      fd.write("\ndef foo():\n    pass\n")
            self.assertFalse('foo' in plugin.get_set().get().keys())
            self.projector("gui-scripts add foo a.b.c:foo")
            self.assertTrue('foo' in plugin.get_set().get().keys())
            self.projector("gui-scripts remove foo")
            self.assertFalse('foo' in plugin.get_set().get().keys())

    def test_list(self):
        from infi.projector.plugins.builtins.gui_scripts import GuiScriptsPlugin
        from mock import patch, Mock
        with patch("pprint.pprint") as pprint, patch.object(GuiScriptsPlugin, "get_set") as get_set:
            gui_scripts = dict()
            get_set.return_value.get.return_value = gui_scripts
            def side_effect(*args, **kwargs):
                called_gui_scripts, = args
                self.assertEqual(gui_scripts, called_gui_scripts)
            pprint.side_effect = side_effect
            with self.temporary_directory_context():
                self.projector("repository init a.b.c none short long")
                self.projector("gui-scripts list")
                self.assertTrue(pprint.called)
