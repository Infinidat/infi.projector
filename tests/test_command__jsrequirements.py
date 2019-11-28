from .test_case import TestCase
from infi.unittest.parameters import iterate
from contextlib import contextmanager


class JSRequirementsTestCase(TestCase):

    @iterate("package_name", ["jquery=3.2.1", "underscore", "backbone<3.0.0", "angular2>=0.0.0"])
    def test_add_and_remove(self, package_name):
        from infi.projector.plugins.builtins.js_requirements import JSRequirementsPlugin
        from gitpy import LocalRepository
        plugin = JSRequirementsPlugin()
        with self.temporary_directory_context() as dir_path:
            self.projector("repository init a.b.c none short long")
            repository = LocalRepository(dir_path)
            self.assertTrue(repository.isWorkingDirectoryClean())
            self.projector("js-requirements add {} --commit-changes".format(package_name))
            self.assertTrue(repository.isWorkingDirectoryClean())
            self.assertTrue(package_name in plugin.get_package_set().get())
            self.projector("js-requirements remove {} --commit-changes".format(package_name))
            self.assertTrue(repository.isWorkingDirectoryClean())
            self.assertFalse(package_name in plugin.get_package_set().get())

    @contextmanager
    def assert_new_commit(self):
        from gitpy import LocalRepository
        from os import curdir
        repository = LocalRepository(curdir)
        head = repository.getHead().hash
        yield
        self.assertNotEquals(head, repository.getHead().hash)

    def test_freeze_unfreeze(self):
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            self.projector("js-requirements add jquery --commit-changes")
            self.projector("devenv build")
            with self.assert_new_commit():
                self.projector("js-requirements freeze --commit-changes")
            self.assertIn("jquery =", open("buildout.cfg").read())
            self.assertIn('js_versions = True', open("buildout.cfg").read())
            with self.assert_new_commit():
                self.projector("js-requirements unfreeze --commit-changes")
            self.assertNotIn("jquery =", open("buildout.cfg").read())
            self.assertIn("jquery", open("buildout.cfg").read())

    def test_freeze_unfreeze_specific_version(self):
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            self.projector("js-requirements add jquery<3.2.1 --commit-changes")
            self.projector("devenv build")
            with self.assert_new_commit():
                self.projector("js-requirements freeze --commit-changes")
            self.assertIn("[js_versions]", open("buildout.cfg").read())
            self.assertIn("jquery = 3.2.0", open("buildout.cfg").read())
            self.assertIn("jquery<3.2.1", open("buildout.cfg").read())
            with self.assert_new_commit():
                self.projector("js-requirements unfreeze --commit-changes")
            self.assertNotIn("[js_versions]", open("buildout.cfg").read())
            self.assertNotIn("jquery = 3.2.0", open("buildout.cfg").read())
            self.assertIn("jquery<3.2.1", open("buildout.cfg").read())

    def test_freeze_after_freeze(self):
        from gitpy.exceptions import GitCommandFailedException
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            self.projector("js-requirements add jquery=3.3.1 --commit-changes")
            self.projector("devenv build")
            self.projector("js-requirements freeze --commit-changes")
            try:
                self.projector("js-requirements freeze --commit-changes")
            except GitCommandFailedException as e:
                self.assertTrue('clean' in e.msg.lower())
            self.assertIn("[js_versions]", open("buildout.cfg").read())
            self.assertIn("jquery = 3.3.1", open("buildout.cfg").read())
