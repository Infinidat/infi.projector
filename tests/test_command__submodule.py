from .test_case import TestCase
from infi.unittest.parameters import iterate
from os import path, curdir

class SubmoduleTestCase(TestCase):
    def test(self):
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            submodule = path.abspath(curdir)
            with self.temporary_directory_context():
                self.projector("repository init a.b.c none short long")
                self.projector("submodule list")
                self.projector("submodule add foo {} origin/master --use-setup-py --commit-changes")
                self.projector("submodule remove foo ")
