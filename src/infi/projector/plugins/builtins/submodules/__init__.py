from infi.projector.plugins import CommandPlugin
from infi.projector.helper import assertions
from infi.projector.helper.utils import open_buildout_configfile, commit_changes_to_buildout
from logging import getLogger

logger = getLogger(__name__)

USAGE = """
Usage:
    projector submodule list
    projector submodule add <name> <repository> <rev> [--commit-changes] [--use-setup-py]
    projector submodule remove <name> [--commit-changes]

Options:
    <name>                  name of submodule to add/remove
    <rev>                   remote branch name (must start with origin) or commit hash, e.g. origin/master
    --use-setup-py          add the setup.py of the submodule to the buildout environment
"""

class SubmodulePlugin(CommandPlugin):
    def get_docopt_string(self):
        return USAGE

    def get_command_name(self):
        return 'submodule'

    def get_methods(self):
        return [self.list, self.add, self.remove]

    @assertions.requires_repository
    def pre_command_assertions(self):
        pass

    def get_submodule_sections(self):
        with open_buildout_configfile() as buildout:
            sections = [section for section in buildout.sections()
                        if buildout.has_option(section, "recipe") and
                        buildout.get(section, "recipe") in ("zerokspot.recipe.git", "gitrecipe", "git-recipe")]
            return sections

    def list(self):
        from pprint import pprint
        pprint(self.get_submodule_sections())

    def add(self):
        with open_buildout_configfile(write_on_exit=True) as buildout:
            name = self.arguments.get("<name>")
            if name not in self.get_submodule_sections():
                buildout.add_section(name)
            repository = self.arguments.get("<repository>")
            rev = self.arguments.get("<rev>")
            buildout.set(name, "recipe", "zerokspot.recipe.git")
            buildout.set(name, "repository", repository)
            buildout.set(name, "rev", rev)
            buildout.set(name, "newest", "true")
            if self.arguments.get("use-setup-py"):
                where_to_look_for_setup_py = set(buildout.get("buildout", "develop").split())
                where_to_look_for_setup_py.add(name)
                buildout.set("buildout", "develop", ' '.join(where_to_look_for_setup_py))
        if self.arguments.get("--commit-changes", False):
            commit_message = "Adding git submodule {}".format(name)
            commit_changes_to_buildout(commit_message)

    def remove(self):
        with open_buildout_configfile(write_on_exit=True) as buildout:
            name = self.arguments.get("<name>")
            if name in self.get_submodule_sections():
                buildout.remove_section(name)
                where_to_look_for_setup_py = set(buildout.get("buildout", "develop").split())
                where_to_look_for_setup_py.discard(name)
                buildout.set("buildout", "develop", ' '.join(where_to_look_for_setup_py))
        if self.arguments.get("--commit-changes", False):
            commit_message = "Removing git submodule {}".format(name)
            commit_changes_to_buildout(commit_message)
