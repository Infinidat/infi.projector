from infi import unittest
from contextlib import contextmanager
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
            yield tempdir
        rmtree(tempdir, ignore_errors=True)

    def projector(self, argv):
        from infi.projector.scripts import projector
        projector(argv if isinstance(argv, list) else argv.split())
