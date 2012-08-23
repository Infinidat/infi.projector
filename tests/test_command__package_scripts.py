from .test_case import TestCase
from infi.unittest.parameters import iterate

class PackageScriptsTestCase(TestCase):
    @iterate("script_arg", ["--post-install", "--pre-uninstall"])
    def test_set(self, script_arg):
        from infi.projector.plugins.builtins.package_scripts import PackageScriptsPlugin
        plugin = PackageScriptsPlugin()
        plugin.arguments = {script_arg: True}
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            self.assertEquals("None", plugin.get_value())
            self.projector("package-scripts set foo " + script_arg)
            self.assertEquals("foo", plugin.get_value())
            self.projector("package-scripts set None " + script_arg)
            self.assertEquals("None", plugin.get_value())

    @iterate("script_arg", ["--post-install", "--pre-uninstall"])
    def test_show(self, script_arg):
        from mock import patch, Mock
        with patch("pprint.pprint") as pprint:
            def side_effect(*args, **kwargs):
                self.assertEquals(str(None), args[0])
            pprint.side_effect = side_effect
            with self.temporary_directory_context():
                self.projector("repository init a.b.c none short long")
                self.projector("package-scripts show " + script_arg)
                self.assertTrue(pprint.called)
