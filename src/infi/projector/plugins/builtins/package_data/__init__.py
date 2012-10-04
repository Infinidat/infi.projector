from contextlib import contextmanager
from infi.projector.plugins import CommandPlugin
from infi.projector.helper import assertions
from infi.projector.helper.utils import open_buildout_configfile, commit_changes_to_buildout
from infi.projector.helper.utils.package_sets import PackageDataSet
from textwrap import dedent
from logging import getLogger

logger = getLogger(__name__)

USAGE = """
Usage:
    projector package-data list
    projector package-data add <filename> [--commit-changes]
    projector package-data remove <filename> [--commit-changes]

"""

class PackageDataPlugin(CommandPlugin):
    def get_docopt_string(self):
        return USAGE

    def get_command_name(self):
        return 'package-data'

    @assertions.requires_repository
    def parse_commandline_arguments(self, arguments):
        methods = [self.list, self.add, self.remove]
        [method] = [method for method in methods
                    if arguments.get(method.__name__)]
        self.arguments = arguments
        method()

    def get_package_set(self):
        return PackageDataSet()

    def list(self):
        from pprint import pprint
        pprint(list(self.get_package_set().get()))

    def write_manifest_in(self, data_set):
        with open("MANIFEST.in", 'w') as fd:
            fd.write("recursive-include src {}\n".format(' '.join(data_set)))

    def remove(self):
        package_set = self.get_package_set()
        data_set = package_set.get()
        filename = self.arguments.get('<filename>')
        if filename in data_set:
            data_set.remove(filename)
            package_set.set(data_set)
        self.write_manifest_in(data_set)
        if self.arguments.get("--commit-changes", False):
            commit_message = "removing {} from package data".format(filename)
            commit_changes_to_buildout(commit_message)

    def add(self):
        package_set = self.get_package_set()
        data_set = package_set.get()
        filename = self.arguments.get('<filename>')
        if filename not in data_set:
            data_set.add(filename)
            package_set.set(data_set)
        self.write_manifest_in(data_set)
        if self.arguments.get("--commit-changes", False):
            commit_message = "adding {} to package data".format(filename)
            commit_changes_to_buildout(commit_message)
