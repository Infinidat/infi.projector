from .test_case import TestCase
from infi.unittest.parameters import iterate

class PackageDataTestCase(TestCase):
    @iterate("package_data", ["filename"])
    def test_add_and_remove(self, package_data):
        from infi.projector.plugins.builtins.package_data import PackageDataPlugin
        plugin = PackageDataPlugin()
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            self.projector("package-data add {}".format(package_data))
            self.assertTrue(package_data in plugin.get_package_set().get())
            self.projector("package-data remove {}".format(package_data))
            self.assertFalse(package_data in plugin.get_package_set().get())

    def test_list(self):
        from infi.projector.plugins.builtins.package_data import PackageDataPlugin
        from mock import patch, Mock
        with patch("pprint.pprint") as pprint:
            def side_effect(*args, **kwargs):
                self.assertEquals([], args[0])
            pprint.side_effect = side_effect
            with self.temporary_directory_context():
                self.projector("repository init a.b.c none short long")
                self.projector("package-data list")
                self.assertTrue(pprint.called)
