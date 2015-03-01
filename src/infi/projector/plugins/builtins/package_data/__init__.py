from infi.projector.plugins import CommandPlugin
from infi.projector.helper import assertions
from infi.projector.helper.utils import commit_changes_to_buildout, commit_changes_to_manifest_in
from infi.projector.helper.utils.package_sets import PackageDataSet
from logging import getLogger

logger = getLogger(__name__)

USAGE = """
Usage:
    projector package-data list
    projector package-data add <filename> [--commit-changes]
    projector package-data remove <filename> [--commit-changes]

Options:
    <filename>              file to add
"""

class PackageDataPlugin(CommandPlugin):
    def get_docopt_string(self):
        return USAGE

    def get_command_name(self):
        return 'package-data'

    def get_methods(self):
        return [self.list, self.add, self.remove]

    @assertions.requires_repository
    def pre_command_assertions(self):
        pass

    def get_package_set(self):
        return PackageDataSet()

    def list(self):
        from pprint import pprint
        pprint(sorted(list(self.get_package_set().get()), key=lambda s: s.lower()))

    def write_manifest_in(self, data_set):
        data_list = sorted(list(data_set), key=lambda s: s.lower())
        with open("MANIFEST.in", 'w') as fd:
            fd.write("recursive-include src {}\n".format(' '.join(data_list)))

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
            commit_changes_to_manifest_in(commit_message)

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
            commit_changes_to_manifest_in(commit_message)
