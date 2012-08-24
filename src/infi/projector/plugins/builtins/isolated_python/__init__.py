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
    projector isolated-python python-version get
    projector isolated-python python-version set <version> [--commit-changes]
"""

class IsolatedPythonPlugin(CommandPlugin):
    def get_docopt_string(self):
        return USAGE

    def get_command_name(self):
        return 'isolated-python'

    @assertions.requires_repository
    def parse_commandline_arguments(self, arguments):
        methods = [self.python_version]
        [method] = [method for method in methods
                    if arguments.get(method.__name__.replace('_', '-'))]
        self.arguments = arguments
        method()

    def get_package_set(self):
        return PackageDataSet()

    def python_version(self):
        with open_buildout_configfile(write_on_exit=self.arguments.get("set")) as buildout:
            sections = [section for section in buildout.sections()
                        if buildout.has_option(section, "recipe") and \
                        buildout.get(section, "recipe") == "infi.recipe.python"]
            if not sections: # pragma: no cover
                logger.error("isolated python section not found in buildout.cfg")
                raise SystemExit(1)
            if self.arguments.get("get"):
                print buildout.get(sections[0], "version")
            elif self.arguments.get("set"):
                version = self.arguments.get("<version>")
                buildout.set(sections[0], "version", version)
                if self.arguments.get("--commit-changes", False):
                    commit_message = "changed isolated python version to {}".format(version)
                    commit_changes_to_buildout(commit_message)
