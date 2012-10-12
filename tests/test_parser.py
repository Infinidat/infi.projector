from .test_case import TestCase
from mock import patch

class TestParser(TestCase):
    def test_help(self):
        with self.assertRaises(SystemExit):
            self.projector("-h")

    def test_version(self):
        self.projector("-v")

def expanduser(*args, **kwargs):
    return '.infiproject'

class ConfigFileParserTests(TestCase):
    def test_configfile_does_not_exist(self):
        with self.temporary_directory_context():
            with patch("os.path.expanduser", new=expanduser):
                from infi.projector.commandline_parser import append_default_arguments_from_configuration_files
                arguments = dict()
                append_default_arguments_from_configuration_files(arguments)
                self.assertEquals(arguments, dict())

    def test_configfile_no_commanline_section(self):
        with self.temporary_directory_context():
            with open(".infiproject", 'w') as fd:
                fd.write("[invalid-section]\n")
            with patch("os.path.expanduser", new=expanduser):
                from infi.projector.commandline_parser import append_default_arguments_from_configuration_files
                arguments = dict()
                append_default_arguments_from_configuration_files(arguments)
                self.assertEquals(arguments, dict())

    def test_configfile_some_commandline_arguments(self):
        with self.temporary_directory_context():
            with open(".infiproject", 'w') as fd:
                fd.write("[commandline-arguments]\n--use-isolated-python = True\n--pypi-servers=pypi,local\n")
            with patch("os.path.expanduser", new=expanduser):
                from infi.projector.commandline_parser import append_default_arguments_from_configuration_files
                arguments = dict()
                append_default_arguments_from_configuration_files(arguments)
                expected = {'--pypi-servers': 'pypi,local', '--use-isolated-python': True}
                self.assertEquals(arguments, expected)
