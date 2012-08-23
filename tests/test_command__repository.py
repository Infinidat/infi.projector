from .test_case import TestCase
from os import path, curdir, listdir, makedirs
from infi.projector.helper import utils

class RepositoryTestCase(TestCase):
    def assert_is_empty(self):
        self.assertEquals(listdir(curdir), [])

    def assert_project_checked_out(self):
        self.assertTrue(path.exists(".git"))
        self.assertTrue(path.exists("bootstrap.py"))
        self.assertTrue(path.exists("setup.in"))

    def test_init(self):
        with self.temporary_directory_context():
            self.assert_is_empty()
            self.projector("repository init a.b.c none short long")
            self.assert_project_checked_out()

    def test_init__mkdir(self):
        with self.temporary_directory_context():
            self.assert_is_empty()
            self.projector("repository init --mkdir a.b.c none short long")
            with utils.chdir('a.b.c'):
                self.assert_project_checked_out()

   def test_init__mkdir_already_exists(self):
        with self.temporary_directory_context():
            self.assert_is_empty()
            makdirs('a.b.c')
            with self.assertRaises(SystemExit):
                self.projector("repository init --mkdir a.b.c none short long")

   def test_init__dotgit_exists(self):
        with self.temporary_directory_context():
            self.assert_is_empty()
            makdirs(".git")
            with self.assertRaises(SystemExit):
                self.projector("repository init a.b.c none short long")

    def test_clone(self):
        from os import curdir
        from os.path import abspath
        with self.temporary_directory_context():
            self.projector("repository init --mkdir a.b.c none short long")
            origin = abspath(path.join(curdir, 'a.b.c'))
            with self.temporary_directory_context():
                self.assert_is_empty()
                self.projector("repository clone {}".format(origin))
                with utils.chdir('a.b.c'):
                    self.assert_project_checked_out()
