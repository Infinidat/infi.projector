from unittest import SkipTest
from .test_case import TestCase
from os import path, curdir, listdir, makedirs, name
from infi.projector.helper import utils

is_windows = name == "nt"

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

    def test_init__mkdir__name_has_dotgit_in_the_middle(self):
        with self.temporary_directory_context():
            self.assert_is_empty()
            self.projector("repository init --mkdir a.b.gitsomething.foo none short long")
            self.assertTrue(path.exists("a.b.gitsomething.foo"))

    def test_init__mkdir__name_endswith_dotgit(self):
        with self.temporary_directory_context():
            self.assert_is_empty()
            self.projector("repository init --mkdir a.b.git none short long")
            self.assertTrue(path.exists("a.b"))

    def test_init__mkdir_already_exists(self):
        with self.temporary_directory_context():
            self.assert_is_empty()
            makedirs('a.b.c')
            with self.assertRaises(SystemExit):
                self.projector("repository init --mkdir a.b.c none short long")

    def test_init__dotgit_exists(self):
        with self.temporary_directory_context():
            self.assert_is_empty()
            makedirs(".git")
            with self.assertRaises(SystemExit):
                self.projector("repository init a.b.c none short long")

    def test_clone(self):
        from os import curdir, name
        from os.path import abspath
        if is_windows:
            raise SkipTest("skipping test on windows")
        with self.temporary_directory_context():
            self.projector("repository init --mkdir a.b.c none short long")
            origin = abspath(path.join(curdir, 'a.b.c'))
            with self.temporary_directory_context():
                self.assert_is_empty()
                self.projector("repository clone {}".format(origin))
                with utils.chdir('a.b.c'):
                    self.assert_project_checked_out()
