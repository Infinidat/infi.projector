from .test_case import TestCase
from infi.unittest.parameters import iterate

class IsolatedPythonVersion(TestCase):
    def test(self):
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            self.projector("isolated-python python-version get")
            self.projector("isolated-python python-version set v2.7.5.5 --commit-changes")
