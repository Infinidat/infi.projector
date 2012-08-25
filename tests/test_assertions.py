from .test_case import TestCase
from infi.projector.helper import assertions
from infi.unittest.parameters import iterate
from os import makedirs, remove

def touch(filepath):
    with open(filepath, 'a'):
        pass

ASSERTION_FUNCS = [
                   assertions.assert_git_repository,
                   assertions.assert_setup_py_exists,
                   assertions.assert_buildout_configfile_exists,
                   assertions.assert_buildout_executable_exists,
                   assertions.assert_isolated_python_exists,
]

class AssertionsTestCase(TestCase):
    @iterate("assertion_func", ASSERTION_FUNCS)
    def test_assertions_on_empty_directory(self, assertion_func):
        with self.temporary_directory_context():
            with self.assertRaises(SystemExit):
                assertion_func()
