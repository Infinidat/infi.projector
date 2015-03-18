from infi.projector.plugins import CommandPlugin
from infi.projector.helper import assertions
from infi.projector.helper.utils import commit_changes_to_buildout
from infi.projector.helper.utils.package_sets import GuiScriptsSet
from logging import getLogger

logger = getLogger(__name__)

USAGE = """
Usage:
    projector gui-scripts list
    projector gui-scripts add <script-name> <entry-point> [--commit-changes]
    projector gui-scripts remove <script-name> [--commit-changes]
"""

class GuiScriptsPlugin(CommandPlugin):
    def get_docopt_string(self):
        return USAGE

    def get_command_name(self):
        return 'gui-scripts'

    def get_methods(self):
        return [self.list, self.add, self.remove]

    @assertions.requires_repository
    def pre_command_assertions(self):
        pass

    def get_set(self):
        return GuiScriptsSet()

    def list(self):
        from pprint import pprint
        pprint(self.get_set().get())

    def remove(self):
        package_set = self.get_set()
        gui_scripts = package_set.get()
        gui_script = self.arguments.get('<script-name>')
        if gui_script in gui_scripts.keys():
            gui_scripts.pop(gui_script)
            package_set.set(gui_scripts)
        if self.arguments.get("--commit-changes", False):
            commit_message = "removing {} from gui_scripts".format(gui_script)
            commit_changes_to_buildout(commit_message)

    def add(self):
        package_set = self.get_set()
        gui_scripts = package_set.get()
        script_name = self.arguments.get('<script-name>')
        gui_scripts[script_name] = self.arguments.get('<entry-point>')
        package_set.set(gui_scripts)
        if self.arguments.get("--commit-changes", False):
            commit_message = "adding {} to gui_scripts".format(script_name)
            commit_changes_to_buildout(commit_message)
