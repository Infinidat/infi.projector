from contextlib import contextmanager
from infi.projector.plugins import CommandPlugin
from infi.projector.helper import assertions
from infi.projector.helper.utils import open_buildout_configfile, commit_changes_to_buildout
from textwrap import dedent
from logging import getLogger

logger = getLogger(__name__)

USAGE = """
Usage:
    projector package-scripts show (--post-install | --pre-uninstall)
    projector package-scripts set <value> (--post-install | --pre-uninstall) [--commit-changes]

Options:
    <value>     the exectuable basename, under the 'bin' directory (e.g. projector). Set None to disable.
"""

class PackageScriptsPlugin(CommandPlugin):
    def get_docopt_string(self):
        return USAGE

    def get_command_name(self):
        return 'package-scripts'

    @assertions.requires_repository
    def parse_commandline_arguments(self, arguments):
        methods = [self.show, self.set]
        [method] = [method for method in methods
                    if arguments.get(method.__name__)]
        self.arguments = arguments
        method()

    def get_attribute(self):
        if self.arguments.get('--post-install'):
            return "post_install_script_name"
        if self.arguments.get('--pre-uninstall'):
            return "pre_uninstall_script_name"

    def get_value(self):
        with open_buildout_configfile() as buildout_cfg:
            return buildout_cfg.get("project", self.get_attribute())

    def set_value(self, value):
        with open_buildout_configfile(write_on_exit=True) as buildout_cfg:
            return buildout_cfg.set("project", self.get_attribute(), value)

    def show(self):
        from pprint import pprint
        pprint(self.get_value())

    def set(self):
        value = self.arguments.get('<value>')
        self.set_value(value)
        if self.arguments.get("--commit-changes", False):
            commit_message = "setting {} to {}".format(self.get_attribute(), value)
            commit_changes_to_buildout(commit_message)
