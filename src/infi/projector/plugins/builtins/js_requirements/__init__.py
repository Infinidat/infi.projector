import os
from infi.projector.plugins import CommandPlugin
from infi.projector.helper import assertions
from infi.projector.helper.utils import commit_changes_to_buildout, open_buildout_configfile
from infi.projector.helper.utils.package_sets import RepresentedListSet
from logging import getLogger

logger = getLogger(__name__)

USAGE = """
Usage:
    projector js-requirements list
    projector js-requirements add <requirement> [--commit-changes]
    projector js-requirements remove <requirement> [--commit-changes]
    projector js-requirements freeze [--commit-changes] [--push-changes]
    projector js-requirements unfreeze [--commit-changes] [--push-changes]


Options:
    js-requirement list               Show all js-requirement
    js-requirement add                add a package to the list of project js-requirement
    js-requirement remove             remove a package from project requirement list
    js-requirement freeze             Creates a js_versions section (based on .package-lock.json, telling buildout to use specific versions)
    js-requirement unfreeze           Deletes the js_versions section, if it exists
    <requirement>                     requirement to add/remove
"""


class JSRequirementsPlugin(CommandPlugin):
    DEFAULT_DIRECTORY = "parts/js/"

    def get_docopt_string(self):
        return USAGE

    def get_command_name(self):
        return 'js-requirements'

    def get_methods(self):
        return [self.list, self.add, self.remove, self.freeze, self.unfreeze]

    def get_package_set(self):
        return RepresentedListSet('js-requirements', 'javascript-packages')

    def list(self):
        from pprint import pprint
        pkg_set = self.get_package_set()
        if pkg_set.get():
            pprint(sorted(list(pkg_set.get()), key=lambda s: s.lower()))
        else:
            print('Please initiate js-requirements first by using "add" argument.')

    def remove(self):
        package_set = self.get_package_set()
        requirements = package_set.get()
        requirement = self.arguments.get('<requirement>')
        if requirement in requirements:
            requirements.remove(requirement)
            package_set.set(requirements)
        if self.arguments.get("--commit-changes", False):
            commit_message = "remove {} from js-requirements".format(requirement)
            commit_changes_to_buildout(commit_message)

    def add(self):
        with open_buildout_configfile(write_on_exit=True) as buildout_cfg:
            if not buildout_cfg.has_section("js-requirements"):
                buildout_cfg.add_section("js-requirements")
                buildout_cfg.set("js-requirements", "recipe", "infi.recipe.js_requirements")
                buildout_cfg.set("js-requirements", "js-directory", "")
                buildout_cfg.set("js-requirements", "symlink-to-directory", "parts/js")
                buildout_cfg.set("js-requirements", "javascript-packages", "[]")

        package_set = self.get_package_set()
        requirements = package_set.get()
        requirement = self.arguments.get('<requirement>')
        if requirement not in requirements:
            requirements.add(requirement)
            package_set.set(requirements)
        if self.arguments.get("--commit-changes", False):
            commit_message = "adding {} to js-requirements".format(requirement)
            commit_changes_to_buildout(commit_message)

    def freeze(self):
        from gitpy import LocalRepository
        from os import curdir
        import json

        # Read/write the buildout.cfg
        with open_buildout_configfile(write_on_exit=True) as buildout_cfg:
            if not buildout_cfg.has_section('js-requirements'):
                print("Missing js-requirements section")
                return
            packages_path = buildout_cfg.get('js-requirements', 'js-directory') or self.DEFAULT_DIRECTORY
            try:
                with open(os.path.join(packages_path, '.package-lock.json'), 'r') as pljson:
                    selected_versions = json.load(pljson)
                    if buildout_cfg.has_section("js_versions"):
                        buildout_cfg.remove_section("js_versions")
                    buildout_cfg.add_section("js_versions")
                for key in sorted(selected_versions.keys(), key=lambda s: s.lower()):
                    buildout_cfg.set("js_versions", key, selected_versions[key])
                buildout_cfg.set('buildout', 'js_versions', True)
            except IOError as e:
                import errno
                print(e.message)
                if e.errno == errno.ENOENT:
                    print('.package-lock.json file is missing, try running projector devenv build to create the file')

        # Git operations
        repository = LocalRepository(curdir)
        if self.arguments.get("--commit-changes", False):
            repository.add("buildout.cfg")
            repository.commit("Freezing javascript dependencies")
        push_changes = self.arguments.get("--push-changes", False)
        if push_changes:
            repository._executeGitCommandAssertSuccess("git push")

    def unfreeze(self):
        from gitpy import LocalRepository
        from os import curdir
        with open_buildout_configfile(write_on_exit=True) as buildout_cfg:
            if not buildout_cfg.has_section('js-requirements'):
                print("Missing js-requirements section")
                return
            buildout_cfg.remove_option("buildout", "js_versions")
            buildout_cfg.remove_section("js_versions")

        # Git operations
        repository = LocalRepository(curdir)
        if self.arguments.get("--commit-changes", False):
            repository.add("buildout.cfg")
            repository.commit("Unfreezing javascript dependencies")
        push_changes = self.arguments.get("--push-changes", False)
        if push_changes:
            repository._executeGitCommandAssertSuccess("git push")
