from .test_case import TestCase
from infi.unittest.parameters import iterate

class RequirementsTestCase(TestCase):

    @iterate("development_flag", [True, False])
    @iterate("package_name", ["distribute", "ipython", "does-not-exist"])
    def test_add_and_remove(self, development_flag, package_name):
        from infi.projector.plugins.builtins.requirements import RequirementsPlugin
        plugin = RequirementsPlugin()
        plugin.arguments = {'--development': development_flag}
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            self.projector("requirements add {} {}".format(package_name,
                                                           '--development' if development_flag else ''))
            self.assertTrue(package_name in plugin.get_package_set().get())
            self.projector("requirements remove {} {}".format(package_name,
                                                           '--development' if development_flag else ''))
            self.assertFalse(package_name in plugin.get_package_set().get())

    @iterate("development_flag", [True, False])
    def test_list(self, development_flag):
        from infi.projector.plugins.builtins.requirements import RequirementsPlugin
        from mock import patch, Mock
        with patch("pprint.pprint") as pprint, patch.object(RequirementsPlugin, "get_package_set") as get_package_set:
            requirements = set(['distribute'])
            get_package_set.return_value.get.return_value = requirements
            def side_effect(*args, **kwargs):
                called_requirements, = args
                self.assertEquals(list(requirements), called_requirements)
            pprint.side_effect = side_effect
            with self.temporary_directory_context():
                self.projector("repository init a.b.c none short long")
                self.projector("requirements list {}".format('--development' if development_flag else ''))
                self.assertTrue(pprint.called)
