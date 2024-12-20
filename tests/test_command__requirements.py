from .test_case import TestCase
from infi.unittest.parameters import iterate
from contextlib import contextmanager

class RequirementsTestCase(TestCase):

    @iterate("development_flag", [True, False])
    @iterate("package_name", ["distribute", "ipython", "does-not-exist"])
    def test_add_and_remove(self, development_flag, package_name):
        from infi.projector.plugins.builtins.requirements import RequirementsPlugin
        from infi.gitpy import LocalRepository
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
                self.assertEqual(list(requirements), called_requirements)
            pprint.side_effect = side_effect
            with self.temporary_directory_context():
                self.projector("repository init a.b.c none short long")
                self.projector("requirements list {}".format('--development' if development_flag else ''))
                self.assertTrue(pprint.called)

    @contextmanager
    def assert_new_commit(self):
        from infi.gitpy import LocalRepository
        from os import curdir
        repository = LocalRepository(curdir)
        head = repository.getHead().hash
        yield
        self.assertNotEqual(head, repository.getHead().hash)

    def _clear_development_requirements(self):
        self.projector("requirements remove infi.traceback --commit-changes --development")
        self.projector("requirements remove infi.unittest --commit-changes --development")
        self.projector("requirements remove ipython --commit-changes --development")
        self.projector("requirements remove nose --commit-changes --development")

    def test_freeze_unfreeze_case_insensitive(self):
        from os import path
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            self.projector("requirements add PrettyTable --commit-changes")
            self._clear_development_requirements()
            self.projector("devenv build --use-isolated-python --prefer-final")
            with self.assert_new_commit():
                self.projector("requirements freeze --with-install-requires --commit-changes --strip-suffix-from-post-releases")
            self.assertIn("prettytable =", open("buildout.cfg").read())
            self.assertIn("PrettyTable>=", open("buildout.cfg").read())
            with self.assert_new_commit():
                self.projector("requirements unfreeze --commit-changes --with-install-requires")
            self.assertNotIn("prettytable =", open("buildout.cfg").read())
            self.assertNotIn("PrettyTable>=", open("buildout.cfg").read())
            self.assertIn("PrettyTable", open("buildout.cfg").read())

    def test_freeze_unfreeze(self):
        from os import path
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            self.projector("requirements add Flask==1.0.3 --commit-changes")
            self._clear_development_requirements()
            self.projector("devenv build --use-isolated-python --prefer-final")
            with self.assert_new_commit():
                self.projector("requirements freeze --with-install-requires --commit-changes --strip-suffix-from-post-releases")
            self.assertIn("[versions]", open("buildout.cfg").read())
            self.assertIn("Flask==1.0.3", open("buildout.cfg").read())
            self.assertIn("setuptool", open("buildout.cfg").read())
            with self.assert_new_commit():
                self.projector("requirements unfreeze --commit-changes --with-install-requires")
            self.assertIn("[versions]", open("buildout.cfg").read())
            self.assertIn("Flask==1.0.3", open("buildout.cfg").read())
            self.assertIn("Flask = 1.0.3", open("buildout.cfg").read())

    def test_freeze_unfreeze__no_specific_dependencies(self):
        from os import path
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            self.projector("requirements remove infi.traceback --commit-changes --development")
            self.projector("requirements remove infi.unittest --commit-changes --development")
            self.projector("requirements remove ipython --commit-changes --development")
            self.projector("requirements remove nose --commit-changes --development")
            self.projector("devenv build --use-isolated-python --prefer-final")
            with self.assert_new_commit():
                self.projector("requirements freeze --with-install-requires --commit-changes --strip-suffix-from-post-releases")
            self.assertIn("[versions]", open("buildout.cfg").read())
            self.assertIn("setuptool", open("buildout.cfg").read())
            with self.assert_new_commit():
                self.projector("requirements unfreeze --commit-changes --with-install-requires")
            self.assertNotIn("[versions]", open("buildout.cfg").read())

    def test_freeze_after_freeze(self):
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            self.projector("requirements add Flask==1.0.3 --commit-changes")
            self.projector("requirements remove infi.traceback --commit-changes --development")
            self.projector("requirements remove infi.unittest --commit-changes --development")
            self.projector("requirements remove ipython --commit-changes --development")
            self.projector("requirements remove nose --commit-changes --development")
            self.projector("devenv build --use-isolated-python --prefer-final")
            self.projector("requirements freeze --with-install-requires --commit-changes --strip-suffix-from-post-releases")
            self.projector("requirements freeze --with-install-requires --strip-suffix-from-post-releases")
            self.assertIn("[versions]", open("buildout.cfg").read())
            self.assertIn("Flask==1.0.3", open("buildout.cfg").read())
            self.assertIn("setuptools", open("buildout.cfg").read())
