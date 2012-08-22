from contextlib import contextmanager
from infi.projector.plugins import CommandPlugin
from infi.projector.helper import assertions
from infi.projector.helper.utils import open_buildout_configfile
from textwrap import dedent
from logging import getLogger

logger = getLogger(__name__)

USAGE = """
Usage:
    projector requirements list [--development]
    projector requirements add <requirement> [--development]
    projector requirements remove <requirement> [--development]

Options:
    --development       Requirement for the development environment only
"""

class PackageSet(object):
    @classmethod
    def get(cls):
        raise NotImplementedError()

    @classmethod
    def set(cls, package_set):
        raise NotImplementedError()

class InstallRequiresPackageSet(PackageSet):
    @classmethod
    def get(cls):
        with open_buildout_configfile() as buildout_cfg:
            return set(eval(buildout_cfg.get('project', "install_requires")))

    @classmethod
    def set(cls, package_set):
        with open_buildout_configfile() as buildout_cfg:
            buildout_cfg.set('project', "install_requires", repr(list(set(package_set))))

class EggsPackageSet(PackageSet):
    @classmethod
    def _get_section(self):
        with open_buildout_configfile() as buildout:
            sections = [section for section in buildout.sections()
                        if buildout.has_option(section, "recipe") and \
                        buildout.get(section, "recipe") == "infi.vendata.console_scripts"]
            return sections[0]

    @classmethod
    def get(cls):
        with open_buildout_configfile() as buildout_cfg:
            return set(buildout_cfg.get(cls._get_section(), "eggs").splitlines())

    @classmethod
    def set(cls, package_set):
        with open_buildout_configfile() as buildout_cfg:
            newline = '\r\n' if assertions.is_windows() else '\n'
            buildout_cfg.set(cls._get_section(), "eggs", newline.join(list(set(package_set))))

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
        return EggsPackageSet if self.arguments.get("--development", False) else InstallRequiresPackageSet

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

    def add(self):
        package_set = self.get_package_set()
        requirements = package_set.get()
        requirement = self.arguments.get('<requirement>')
        if requirement not in requirements:
            requirements.add(requirement)
            package_set.set(requirements)
