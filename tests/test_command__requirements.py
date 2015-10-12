from .test_case import TestCase
from infi.unittest.parameters import iterate
from infi.pyutils.contexts import contextmanager

class RequirementsTestCase(TestCase):

    @iterate("development_flag", [True, False])
    @iterate("package_name", ["distribute", "ipython", "does-not-exist"])
    def test_add_and_remove(self, development_flag, package_name):
        from infi.projector.plugins.builtins.requirements import RequirementsPlugin
        from gitpy import LocalRepository
        from os import curdir
        plugin = RequirementsPlugin()
        plugin.arguments = {'--development': development_flag}
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            repository = LocalRepository('.')
            self.assertTrue(repository.isWorkingDirectoryClean())
            self.projector("requirements add {} {} --commit-changes".format(package_name,
                                                           '--development' if development_flag else ''))
            self.assertTrue(repository.isWorkingDirectoryClean())
            self.assertTrue(package_name in plugin.get_package_set().get())
            self.projector("requirements remove {} {} --commit-changes".format(package_name,
                                                           '--development' if development_flag else ''))
            self.assertTrue(repository.isWorkingDirectoryClean())
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

    @contextmanager
    def assert_new_commit(self):
        from gitpy import LocalRepository
        from os import curdir
        repository = LocalRepository(curdir)
        head = repository.getHead().hash
        yield
        self.assertNotEquals(head, repository.getHead().hash)

    def test_freeze_unfreeze(self):
        from os import path
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            self.projector("requirements add Flask==0.9 --commit-changes")
            self.projector("requirements remove infi.traceback --commit-changes --development")
            self.projector("requirements remove infi.unittest --commit-changes --development")
            self.projector("requirements remove ipython --commit-changes --development")
            self.projector("requirements remove nose --commit-changes --development")
            self.projector("devenv build --no-readline --use-isolated-python")
            with self.assert_new_commit():
                self.projector("requirements freeze --with-install-requires --newest --commit-changes")
            self.assertIn("[versions]", open("buildout.cfg").read())
            self.assertIn("Flask==0.9", open("buildout.cfg").read())
            self.assertIn("setuptool", open("buildout.cfg").read())
            with self.assert_new_commit():
                self.projector("requirements unfreeze --commit-changes --with-install-requires")
            self.assertNotIn("[versions]", open("buildout.cfg").read())
            self.assertIn("Flask==0.9", open("buildout.cfg").read())

    def test_freeze_after_freeze(self):
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            self.projector("requirements add Flask==0.9 --commit-changes")
            self.projector("requirements remove infi.traceback --commit-changes --development")
            self.projector("requirements remove infi.unittest --commit-changes --development")
            self.projector("requirements remove ipython --commit-changes --development")
            self.projector("requirements remove nose --commit-changes --development")
            self.projector("devenv build --no-readline --use-isolated-python")
            self.projector("requirements freeze --with-install-requires --newest --commit-changes")
            self.projector("requirements freeze --with-install-requires --newest")
            self.assertIn("[versions]", open("buildout.cfg").read())
            self.assertIn("Flask==0.9", open("buildout.cfg").read())
            self.assertIn("setuptools", open("buildout.cfg").read())
