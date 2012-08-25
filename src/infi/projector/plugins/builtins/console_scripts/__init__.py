from contextlib import contextmanager
from infi.projector.plugins import CommandPlugin
from infi.projector.helper import assertions
from infi.projector.helper.utils import open_buildout_configfile, commit_changes_to_buildout
from infi.projector.helper.utils.package_sets import ConsoleScriptsSet
from textwrap import dedent
from logging import getLogger

logger = getLogger(__name__)

USAGE = """
Usage:
    projector console-scripts list
    projector console-scripts add <script-name> <entry-point> [--commit-changes]
    projector console-scripts remove <script-name> [--commit-changes]
"""

class ConsoleScriptsPlugin(CommandPlugin):
    def get_docopt_string(self):
        return USAGE

    def get_command_name(self):
        return 'console-scripts'

    @assertions.requires_repository
    def parse_commandline_arguments(self, arguments):
        methods = [self.list, self.add, self.remove]
        [method] = [method for method in methods
                    if arguments.get(method.__name__)]
        self.arguments = arguments
        method()

    def get_set(self):
        return ConsoleScriptsSet()

    def list(self):
        from pprint import pprint
        pprint(self.get_set().get())

    def remove(self):
        package_set = self.get_set()
        consle_scripts = package_set.get()
        console_script = self.arguments.get('<script-name>')
        if console_script in consle_scripts.keys():
            consle_scripts.pop(console_script)
            package_set.set(consle_scripts)
        if self.arguments.get("--commit-changes", False):
            commit_message = "removing {} from console_scripts".format(console_script)
            commit_changes_to_buildout(commit_message)

    def add(self):
        package_set = self.get_set()
        consle_scripts = package_set.get()
        script_name = self.arguments.get('<script-name>')
        consle_scripts[script_name] = self.arguments.get('<entry-point>')
        package_set.set(consle_scripts)
        if self.arguments.get("--commit-changes", False):
            commit_message = "adding {} to console_scripts".format(script_name)
            commit_changes_to_buildout(commit_message)
