from infi import unittest
from infi.pyutils.contexts import contextmanager
from os import path, curdir

PROJECTOR_BASE_DIR = path.abspath(curdir)

class TestCase(unittest.TestCase):
    @contextmanager
    def temporary_directory_context(self):
        from tempfile import mkdtemp
        from shutil import rmtree
        from infi.projector.helper.utils import chdir
        tempdir = mkdtemp()
        with chdir(tempdir):
            yield
        rmtree(tempdir)

    def projector(self, argv):
        from infi.projector.scripts import projector
        projector(argv if isinstance(argv, list) else argv.split())
