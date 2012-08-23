from contextlib import contextmanager
from infi.projector.plugins import CommandPlugin
from infi.projector.helper import assertions
from infi.projector.helper.utils import open_buildout_configfile
from textwrap import dedent
from logging import getLogger

logger = getLogger(__name__)

USAGE = """
Usage:
    projector console-scripts list
    projector console-scripts add <script-name> <entry-point>
    projector console-scripts remove <script-name>
"""

class ConsoleScriptsSet(object):
    @classmethod
    def get(cls):
        with open_buildout_configfile() as buildout_cfg:
            formatted_entrypoints = (eval(buildout_cfg.get('project', "console_scripts")))
        return {name.strip():entry_point.strip()
                for name, entry_point in [item.split('=') for item in formatted_entrypoints]}

    @classmethod
    def set(cls, console_scripts_dict):
        formatted_entrypoints = ["{} = {}".format(key, value) for key, value in console_scripts_dict.items()]
        with open_buildout_configfile() as buildout_cfg:
            buildout_cfg.set('project', "console_scripts", repr(formatted_entrypoints))

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
        return ConsoleScriptsSet

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

    def add(self):
        package_set = self.get_set()
        consle_scripts = package_set.get()
        consle_scripts[self.arguments.get('<script-name>')] = self.arguments.get('<entry-point>')
        package_set.set(consle_scripts)
