from contextlib import contextmanager
from infi.projector.plugins import CommandPlugin
from infi.projector.helper import assertions, utils
from textwrap import dedent
from logging import getLogger

logger = getLogger(__name__)

USAGE = """
Usage:
    projector devenv build [--clean] [--force-bootstrap] [--no-submodules] [--no-scripts] [--no-readline] [--use-isolated-python] [[--newest] | [--offline]]
    projector devenv relocate ([--absolute] | [--relative]) [--commit-changes]
    projector devenv pack

Options:
    devenv build            use this command to generate setup.py and the console scripts
    devenv relocate         use this command to switch from relative and absolute paths in the console scripts
    devenv pack             create a package, e.g. deb/rpm/msi
    --force-bootstrap       run bootstrap.py even if the buildout script already exists
    --no-submodules         do not clone git sub-modules defined in buildout.cfg
    --no-scripts            do not install the dependent packages, nor create the console scripts. just create setup.py
    --no-readline           do not install [py]readline support (where applicable)
    --use-isolated-python   do not use global system python in console scripts, use Infinidat's isolated python builds
    --newest                always check for new package verson on PyPI
    --offline               install packages only from download cache (no internet connection)
    --clean                 clean build-related files and directories before building
"""

class DevEnvPlugin(CommandPlugin):
    def get_docopt_string(self):
        return USAGE

    def get_command_name(self):
        return 'devenv'

    @assertions.requires_repository
    def parse_commandline_arguments(self, arguments):
        methods = [self.build, self.relocate, self.pack]
        [method] = [method for method in methods
                    if arguments.get(method.__name__)]
        self.arguments = arguments
        method()

    def create_cache_directories(self):
        from os import makedirs
        from os.path import join, exists
        with utils.open_buildout_configfile() as buildout:
            cachedir = buildout.get("buildout", "download-cache")
        cache_dist = join(cachedir, "dist")
        if not exists(cache_dist):
            makedirs(cache_dist)

    def bootstrap_if_necessary(self):
        from os.path import exists, join
        if not exists("bootstrap.py"):
            logger.error("bootsrap.py does not exist")
            raise SystemExit(1)
        buildout_executable_exists = assertions.is_executable_exists(join("bin", "buildout"))
        if not buildout_executable_exists or self.arguments.get("--force-bootstrap", False):
            utils.execute_with_python("bootstrap.py -d")

    def install_sections_by_recipe(self, recipe):
        with utils.open_buildout_configfile() as buildout:
            sections_to_install = [section for section in buildout.sections()
                                   if buildout.has_option(section, "recipe") and \
                                      buildout.get(section, "recipe") == recipe]
        if sections_to_install:
            utils.execute_with_buildout("install {}".format(' '.join(sections_to_install)))

    def submodule_update(self):
        with utils.buildout_parameters_context(['buildout:develop=']):
            self.install_sections_by_recipe("zerokspot.recipe.git")

    def create_setup_py(self):
        with utils.buildout_parameters_context(['buildout:develop=']):
            self.install_sections_by_recipe("infi.recipe.template.version")

    def get_isolated_python_section_name(self):
        with utils.open_buildout_configfile() as buildout:
            sections = [section for section in buildout.sections()
                        if buildout.has_option(section, "recipe") and \
                        buildout.get(section, "recipe").startswith("infi.recipe.python")\
                        and not buildout.get(section, "recipe").endswith(":pack")]
        return sections[0]

    def create_scripts(self):
        self.install_sections_by_recipe("infi.recipe.console_scripts")

    def clean_build(self):
        from os.path import exists
        from os import remove
        from shutil import rmtree
        directories_to_clean = ['bin', 'eggs', 'develop-eggs']
        files_to_clean = ['setup.py']
        _ = [remove(filename) for filename in files_to_clean if exists(filename)]
        _ = [rmtree(dirname)  for dirname in directories_to_clean if exists(dirname)]

    @contextmanager
    def buildout_newest_or_offline_context(self):
        parameters = []
        if self.arguments.get('--newest'):
            parameters.append('-n')
        if self.arguments.get('--offline'):
            parameters.append('-o')
        with utils.buildout_parameters_context(parameters):
            yield

    def get_readline_module(self):
        from platform import system
        modules = {"Darwin": 'readline',
                   "Windows": 'pyreadline'}
        return modules.get(system())

    def is_module_installed(self, module):
        from infi.execute import execute_assert_success, ExecutionError
        try:
            execute_assert_success("bin/python -c import {}".format(module).split())
        except (OSError, ExecutionError): # pragma: no cover
            return False
        return True

    def install_readline(self):
        from platform import system
        from infi.execute import execute_assert_success, ExecutionError
        module = self.get_readline_module()
        if not module or self.is_module_installed(module): # pragma: no cover
            return
        try:
            execute_assert_success("bin/easy_install {}".format(module).split())
        except (OSError, ExecutionError): # pragma: no cover
            logger.warn("distribute is not a requirements, not installing readline support")
            pass

    def install_isolated_python_if_necessary(self):
        from infi.execute import execute_assert_success, ExecutionError
        if not self.arguments.get("--use-isolated-python", False):
            return
        if not assertions.is_isolated_python_exists() or self.arguments.get("--newest", False):
            with utils.buildout_parameters_context(['buildout:develop=']):
                utils.execute_with_buildout("install {}".format(self.get_isolated_python_section_name()))
            self.arguments["--force-bootstrap"] =  True
            utils.execute_with_isolated_python("bootstrap.py -d")

    def build(self):
        if self.arguments.get("--clean", False):
            self.clean_build()
        self.create_cache_directories()
        self.bootstrap_if_necessary()
        with self.buildout_newest_or_offline_context():
            self.install_isolated_python_if_necessary()
            if not self.arguments.get("--no-submodules", False):
                self.submodule_update()
            if not self.arguments.get("--no-setup-py", False):
                self.create_setup_py()
            if not self.arguments.get("--no-scripts", False):
                self.create_scripts()
                if not self.arguments.get("--no-readline", False):
                    self.install_readline()

    def relocate(self):
        from os import curdir
        from gitpy import LocalRepository
        relative_paths = self.arguments.get("--relative", False)
        with utils.open_buildout_configfile(write_on_exit=True) as buildout:
            buildout.set("buildout", "relative-paths", 'true' if relative_paths else 'false')
        if self.arguments.get("--commit-changes", False):
            commit_message = "Changing shebang to {} paths".format("relative" if relative_paths else "absolute")
            utils.commit_changes_to_buildout(commit_message)
        logger.info("Configuration changed. Run `projector devenv build [--use-isolated-python]`.")

    def pack(self):
        assertions.assert_isolated_python_exists()
        self.install_sections_by_recipe("infi.recipe.application_packager")
