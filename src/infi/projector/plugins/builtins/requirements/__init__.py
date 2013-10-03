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
    projector requirements freeze [--with-install-requires] [--newest] [--commit-changes] [--push-changes]
    projector requirements unfreeze [--with-install-requires] [--commit-changes] [--push-changes]


Options:
    requirements list               Show all requirements
    requirements add                add a package to the list of project requirements
    requirements remove             remove a package from project requirement list
    requirements freeze             Creates a versions.cfg file, telling buildout to use specific versions
    requirements unfreeze           Deletes the versions.cfg file, if it exists
    <requirement>                   requirement to add/remove
    --development                   Requirement for the development environment only
    --with-install-requires         Set >= requireements in the install_requires section
    --push-changes                  Push freeze commits
"""

class RequirementsPlugin(CommandPlugin):
    def get_docopt_string(self):
        return USAGE

    def get_command_name(self):
        return 'requirements'

    @assertions.requires_repository
    def parse_commandline_arguments(self, arguments):
        methods = [self.list, self.add, self.remove, self.freeze, self.unfreeze]
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

    def freeze(self):
        from infi.projector.helper.utils import freeze_versions, buildout_parameters_context, open_tempfile
        from infi.projector.plugins.builtins.devenv import DevEnvPlugin
        from gitpy import LocalRepository
        from os import curdir
        plugin = DevEnvPlugin()
        plugin.arguments = {'--newest': self.arguments.get("--newest", False)}
        plugin.arguments = {'--use-isolateded-python': True}
        with open_tempfile() as tempfile:
            with buildout_parameters_context(["buildout:update-versions-file={0}".format(tempfile)]):
                plugin.build()
            with open(tempfile) as fd:
                content = fd.read()
            with open(tempfile, 'w') as fd:
                fd.write("[versions]\n" + content)
            freeze_versions(tempfile, self.arguments.get("--with-install-requires", False))
        if self.arguments.get("--commit-changes", False):
            repository = LocalRepository(curdir)
            repository.add("buildout.cfg")
            repository.commit("Freezing dependencies")
        push_changes = self.arguments.get("--push-changes", False)
        if push_changes:
            repository._executeGitCommandAssertSuccess("git push")

    def unfreeze(self):
        from infi.projector.helper.utils import unfreeze_versions
        from gitpy import LocalRepository
        from os import curdir
        unfreeze_versions(self.arguments.get("--with-install-requires", False))
        if self.arguments.get("--commit-changes", False):
            repository = LocalRepository(curdir)
            repository.add("buildout.cfg")
            repository.commit("Unfreezing dependencies")
        push_changes = self.arguments.get("--push-changes", False)
        if push_changes:
            repository._executeGitCommandAssertSuccess("git push")
