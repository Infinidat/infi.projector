from .test_case import TestCase
from unittest import SkipTest
import sys
from mock import patch
from os import path, pardir, curdir, remove
from infi.projector.helper import utils, assertions

PROJECT_ROOT = path.abspath(path.join(path.dirname(__file__), pardir))

class DevEnvTestCase(TestCase):
    def assert_scripts_were_generated_by_buildout(self):
        self.assertTrue(path.exists("setup.py"))
        self.assertTrue(assertions.is_executable_exists(path.join("bin", "buildout")))
        self.assertTrue(assertions.is_executable_exists(path.join("bin", "python")))
        self.assertTrue(assertions.is_executable_exists(path.join("bin", "ipython")))

    def assert_shebang_line_in_buildout_script_does_not_use_isolated_python(self):
        self.assertFalse(assertions.is_buildout_executable_using_isolated_python())

    def test_build_after_init(self):
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            self.projector("devenv build --clean")
            self.assertFalse(path.exists(path.join("parts", "python")))
            self.assert_scripts_were_generated_by_buildout()
            self.assert_shebang_line_in_buildout_script_does_not_use_isolated_python()
            self.projector("devenv build --newest")
            self.projector("devenv build --offline")
            self.projector("devenv build --use-isolated-python")
            self.projector("devenv build --pack")

    def test_build__no_bootstrap(self):
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            remove("bootstrap.py")
            with self.assertRaises(SystemExit):
                self.projector("devenv build --clean")

    def test_build_after_init__use_isolated_python(self):
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            self.projector("devenv build --use-isolated-python")
            self.assertTrue(path.exists(path.join("parts", "python")))
            self.assert_scripts_were_generated_by_buildout()
            self.assert_shebang_line_in_buildout_script_does_not_use_isolated_python()
            self.projector("devenv build --use-isolated-python --newest")

    def test_build__absolute_paths(self):
        from infi.projector.helper.assertions import is_windows
        from infi.projector.helper.utils import buildout_parameters_context
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            self.projector("devenv relocate --absolute --commit-changes")
            self.projector("devenv build --use-isolated-python --no-readline")
            self.assertTrue(path.exists(path.join("parts", "python")))
            with open(path.join("bin", "python-script.py" if is_windows() else "python")) as fd:
                python_content = fd.read()
            self.assertFalse(python_content.startswith("#!parts/python/bin/python") and not is_windows())

    def execute_assert_success(self, commandline_or_args):
        from infi.execute import execute_assert_success
        args = utils.parse_args(commandline_or_args)
        args[0] += '.exe' if assertions.is_windows() else ''
        execute_assert_success(args)

    def test_build_in_virtualenv(self):
        from infi.execute import ExecutionError
        with self.temporary_directory_context():
            try:
                self.execute_assert_success("virtualenv --distribute virtualenv-python")
            except ExecutionError, error:
                raise SkipTest("Skipping because virtualenv does not work")
            virtualenv_dir = path.abspath(path.join(curdir, 'virtualenv-python'))
            bin_dir = path.join(virtualenv_dir, 'Scripts' if assertions.is_windows() else 'bin')
            python = path.join(bin_dir, 'python')
            with utils.chdir(PROJECT_ROOT):
                self.execute_assert_success("{python} setup.py develop".format(python=python))
            with patch.object(sys, "executable", new=python+'.exe' if assertions.is_windows() else python):
                with patch.object(sys, "real_prefix", new=True, create=True):
                    self.test_build_after_init()
