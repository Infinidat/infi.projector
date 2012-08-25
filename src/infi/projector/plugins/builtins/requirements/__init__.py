from contextlib import contextmanager
from infi.projector.plugins import CommandPlugin
from infi.projector.helper import assertions
from infi.projector.helper.utils import open_buildout_configfile, commit_changes_to_buildout
from infi.projector.helper.utils.package_sets import InstallRequiresPackageSet, EggsPackageSet
from textwrap import dedent
from logging import getLogger

logger = getLogger(__name__)

USAGE = """
Usage:
    projector requirements list [--development]
    projector requirements add <requirement> [--development] [--commit-changes]
    projector requirements remove <requirement> [--development] [--commit-changes]

Options:
    --development       Requirement for the development environment only
"""

class RequirementsPlugin(CommandPlugin):
    def get_docopt_string(self):
        return USAGE

    def get_command_name(self):
        return 'requirements'

    @assertions.requires_repository
    def parse_commandline_arguments(self, arguments):
        methods = [self.list, self.add, self.remove]
        [method] = [method for method in methods
                    if arguments.get(method.__name__)]
        self.arguments = arguments
        method()

    def get_package_set(self):
        return EggsPackageSet() if self.arguments.get("--development", False) else InstallRequiresPackageSet()

    def list(self):
        from pprint import pprint
        pprint(list(self.get_package_set().get()))

    def remove(self):
        package_set = self.get_package_set()
        requirements = package_set.get()
        requirement = self.arguments.get('<requirement>')
        if requirement in requirements:
            requirements.remove(requirement)
            package_set.set(requirements)
        if self.arguments.get("--commit-changes", False):
            message = "remove {} from requirements {}"
            commit_message = message.format(requirement, "(dev)" if self.arguments.get("--development") else '')
            commit_changes_to_buildout(commit_message)

    def add(self):
        package_set = self.get_package_set()
        requirements = package_set.get()
        requirement = self.arguments.get('<requirement>')
        if requirement not in requirements:
            requirements.add(requirement)
            package_set.set(requirements)
        if self.arguments.get("--commit-changes", False):
            message = "adding {} to requirements {}"
            commit_message = message.format(requirement, "(dev)" if self.arguments.get("--development") else '')
            commit_changes_to_buildout(commit_message)
