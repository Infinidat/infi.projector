from contextlib import contextmanager
from infi.projector.plugins import CommandPlugin
from infi.projector.helper import assertions, utils
from infi.projector.helper.utils import configparser
from infi.os_info import get_platform_name, get_platform_string
from logging import getLogger
from six.moves.urllib.request import urlopen
import os

logger = getLogger(__name__)

TOOLKIT_PREFIX = 'toolkit'
TOOLKIT_SUFFIX = 'tar.gz'
REPO_URL = os.path.join('ftp://repo.lab.il.infinidat.com', 'packages', 'main-stable', 'python', TOOLKIT_PREFIX)
INFINIDAT_PATH = os.path.join(os.path.sep, 'opt', 'infinidat')
TOOLKIT_PATH = os.path.join(INFINIDAT_PATH, TOOLKIT_PREFIX)
BIN_PATH = os.path.join(TOOLKIT_PATH, 'bin')

USAGE = """
Usage:
    projector devenv build [--clean] [--force-bootstrap] [--no-submodules] [--no-setup-py] [--no-js-requirements] [--no-scripts] [--use-isolated-python] [[--newest] | [--offline] | [--prefer-final]]
    projector devenv relocate ([--absolute] | [--relative]) [--commit-changes]
    projector devenv pack

Options:
    devenv build            use this command to generate setup.py and the console scripts
    devenv relocate         use this command to switch from relative and absolute paths in the console scripts
    devenv pack             create a package, e.g. deb/rpm/msi
    --clean                 clean build-related files and directories before building
    --force-bootstrap       run buildout bootstrap even if the buildout script already exists
    --no-submodules         do not clone git sub-modules defined in buildout.cfg
    --no-scripts            do not install the dependent packages, nor create the console scripts. just create setup.py
    --use-isolated-python   do not use global system python in console scripts, use Infinidat's isolated python builds
    --newest                always check for new package version on PyPI
    --offline               install packages only from download cache (no internet connection)
    --absolute              change the paths in the development environment to absolute paths
    --relative              change the paths in the development environment to relative paths
    --prefer-final          don't install development versions of dependencies, prefer their latest final versions.
    --no-js-requirements    don't download and extract js-requirements.
"""


class DevEnvPlugin(CommandPlugin):
    def __init__(self):
        self.env = {}
        self.install_toolkit_if_necessary()

    def get_docopt_string(self):
        return USAGE

    def get_command_name(self):
        return 'devenv'

    def get_methods(self):
        return [self.build, self.relocate, self.pack]

    @assertions.requires_repository
    def pre_command_assertions(self):
        pass

    def create_cache_directories(self):
        from os import makedirs
        from os.path import join, exists
        with utils.open_buildout_configfile() as buildout:
            cachedir = buildout.get("buildout", "download-cache")
        cache_dist = join(cachedir, "dist")
        if not exists(cache_dist):
            makedirs(cache_dist)

    def _get_pypi_index_url(self):
        from os import path
        pydistutils = configparser.ConfigParser()
        pydistutils.read([path.expanduser(path.join("~", basename)) for basename in ['.pydistutils.cfg', 'pydistutils.cfg']])
        try:
            return pydistutils.get("easy_install", "index-url").strip("/")
        except (configparser.NoSectionError, configparser.NoOptionError):
            return "https://pypi.python.org/simple"

    def bootstrap_if_necessary(self):
        from os.path import join, split
        from os import name
        from sys import argv
        from pkg_resources import resource_filename
        from infi.projector.plugins.builtins.repository import skeleton
        buildout_executable_exists = assertions.is_executable_exists(join("bin", "buildout"))
        if not buildout_executable_exists or self.arguments.get("--force-bootstrap", False) or self.arguments.get("--newest", False):
            try:
                return utils.execute_assert_success([utils.get_executable('buildout'), 'bootstrap'])
            except OSError:  # workaround for OSX
                pass
            try:
                utils.execute_assert_success(['buildout', 'bootstrap'])
            except OSError:
                dirname, basename = split(argv[0])
                buildout = join(dirname, 'buildout.exe' if name == 'nt' else 'buildout')
                utils.execute_assert_success([buildout, 'bootstrap'])

    def install_sections_by_recipe(self, recipe, stripped=True):
        with utils.open_buildout_configfile() as buildout:
            sections_to_install = [section for section in buildout.sections()
                                   if buildout.has_option(section, "recipe") and
                                      buildout.get(section, "recipe").startswith(recipe)]
        if sections_to_install:
            utils.execute_with_buildout("install {}".format(' '.join(sections_to_install)), stripped=stripped, env=self.env)

    def submodule_update(self):
        with utils.buildout_parameters_context(['buildout:develop=']):
            self.install_sections_by_recipe("zerokspot.recipe.git")
            self.install_sections_by_recipe("gitrecipe")
            self.install_sections_by_recipe("git-recipe")
            self.install_sections_by_recipe("infi.git-recipe")

    def download_js_requirements(self):
        with utils.buildout_parameters_context(['buildout:develop=']):
            self.install_sections_by_recipe('infi.recipe.js_requirements')

    def create_setup_py(self):
        with utils.buildout_parameters_context(['buildout:develop=']):
            self.install_sections_by_recipe("infi.recipe.template.version")

    def get_isolated_python_section_name(self):
        with utils.open_buildout_configfile() as buildout:
            sections = [section for section in buildout.sections()
                        if buildout.has_option(section, "recipe") and
                        buildout.get(section, "recipe").startswith("infi.recipe.python")
                        and not buildout.get(section, "recipe").endswith(":pack")]
        return sections[0]

    def create_scripts(self):
        additional_options = ["buildout:prefer-final=true"] if self.arguments.get("--prefer-final") else []
        with utils.buildout_parameters_context(additional_options):
            self.install_sections_by_recipe("infi.recipe.console_scripts")

    def _remove_files_of_type_recursively(self, root_path, file_type):
        import os
        file_type = file_type if file_type.startswith(".") else "." + file_type
        [[os.remove(os.path.join(p, f)) for f in fs if f.endswith(file_type)] for p, ds, fs in os.walk(root_path)]

    def clean_build(self):
        from os.path import exists
        from os import remove
        from shutil import rmtree
        directories_to_clean = ['bin', 'eggs', 'develop-eggs', 'parts', '.cache']
        files_to_clean = ['setup.py']
        [remove(filename) for filename in files_to_clean if exists(filename)]
        [rmtree(dirname) for dirname in directories_to_clean if exists(dirname)]
        self._remove_files_of_type_recursively("src", "pyc")

    @contextmanager
    def buildout_newest_or_offline_context(self):
        parameters = []
        if self.arguments.get('--newest'):
            parameters.append('-n')
        if self.arguments.get('--offline'):
            parameters.append('-o')
        with utils.buildout_parameters_context(parameters):
            yield

    def _remove_setuptools_egg_link(self):
        # HOSTDEV-1130
        # https://bugs.launchpad.net/zc.buildout/+bug/1210996
        import os
        with utils.open_buildout_configfile() as buildout:
            try:
                develop_eggs_dir = buildout.get("buildout", "develop-eggs-directory")
            except (configparser.NoSectionError, configparser.NoOptionError):
                develop_eggs_dir = "develop-eggs"
            setuptools_egg_link = os.path.join(develop_eggs_dir, "setuptools.egg-link")
            if os.path.exists(setuptools_egg_link):
                os.remove(setuptools_egg_link)

    def _get_pip(self):
        from sys import version_info
        from pkg_resources import resource_filename
        from infi.projector.plugins.builtins.repository import skeleton
        version = (version_info.major, version_info.minor)
        if version > (3, 6):
            name = "get-pip.py"
        elif version > (2, 7):
            name = "get-pip3.py"
        else:
            name = "get-pip2.py"
        get_pip_py = resource_filename(skeleton.__name__, name)
        with open("get-pip.py", "w") as dst:
            with open(get_pip_py) as src:
                dst.write(src.read())

    def _install_setuptools_and_zc_buildout(self):
        from os.path import join, exists
        from os import environ, remove

        with utils.open_buildout_configfile() as buildout:
            cachedir = buildout.get("buildout", "download-cache")
        cache_dist = join(cachedir, "dist")

        cmd = []
        packages = []

        # in case dependencies are frozen, we need to use the frozen version of setuptools and zc.buildout
        with utils.open_buildout_configfile() as buildout:
            for package in ['setuptools', 'zc.buildout', 'pip']:
                if buildout.has_option("versions", package):
                    packages += ['{}=={}'.format(package, buildout.get("versions", package))]
                else:
                    packages += [package]

        env = environ.copy()
        env['PYTHONPATH'] = ''
        for package in packages:
            utils.execute_assert_success([utils.get_isolated_executable('python'), 'get-pip.py', '--upgrade-strategy=only-if-needed', '--prefix=%s' % join('parts', 'python'), package], env=env)
        remove('get-pip.py')
        utils.execute_assert_success([utils.get_isolated_executable('python'), '-m', 'pip', 'download', '--dest', cache_dist] + packages, env=env)

    def install_isolated_python_if_necessary(self):
        from os import environ
        if not self.arguments.get("--use-isolated-python", False):
            return
        self._remove_setuptools_egg_link()
        if not assertions.is_isolated_python_exists() or self.arguments.get("--newest", False):
            with utils.buildout_parameters_context(['buildout:develop=', 'buildout:versions=no', 'no:key=value']):
                utils.execute_with_buildout("install {}".format(self.get_isolated_python_section_name()))
        self._get_pip()
        self._install_setuptools_and_zc_buildout()
        env = environ.copy()
        env['PYTHONPATH'] = ''
        utils.execute_assert_success([utils.get_isolated_executable('buildout'), 'bootstrap'], env=env)

    def build(self):
        if self.arguments.get("--clean", False):
            self.clean_build()
        elif self.arguments.get("--newest", False):
            self._remove_files_of_type_recursively("src", "pyc")
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
            if not self.arguments.get("--no-js-requirements", False):
                self.download_js_requirements()

    def relocate(self):
        relative_paths = self.arguments.get("--relative", False)
        with utils.open_buildout_configfile(write_on_exit=True) as buildout:
            buildout.set("buildout", "relative-paths", 'true' if relative_paths else 'false')
        if self.arguments.get("--commit-changes", False):
            commit_message = "Changing shebang to {} paths".format("relative" if relative_paths else "absolute")
            utils.commit_changes_to_buildout(commit_message)
        logger.info("Configuration changed. Run `projector devenv build [--use-isolated-python]`.")

    def pack(self):
        assertions.assert_isolated_python_exists()

        self.install_sections_by_recipe("infi.recipe.application_packager", stripped=False)

    def get_tarball_name(self, platform):
        request = urlopen(REPO_URL)
        response = request.read()
        data = response.decode()
        lines = data.splitlines()
        prefix = '%s-' % TOOLKIT_PREFIX
        suffix = '-%s.%s' % (platform, SUFFIX)
        versions = []
        for line in lines:
            rows = line.split()
            if not rows:
                continue
            name = rows[-1]
            if not name.startswith(prefix):
                continue
            name = name.replace(prefix, '')
            if not name.endswith(suffix):
                continue
            name = name.replace(suffix, '')
            octets = name.split('.')
            try:
                version = [int(octet) for octet in octets]
            except (ValueError, TypeError)
                continue
            versions.append(version)
        if not versions:
            return None
        versions.sort()
        version = ".".join(versions[-1])
        tarball_name = '%s%s%s' % (prefix, version, suffix)
        return tarball_name

    def install_toolkit_if_necessary(self):
        if not self.arguments.get("--use-isolated-python", False):
            return None
        if 'windows' == get_platform_name():
            return None
        path = os.environ.get('PATH')
        if path:
            paths = [BIN_PATH] + path.split(os.pathsep)
            path = os.pathsep.join(paths)
        else:
            path = BIN_PATH
        shell = os.path.join(BIN_PATH, 'bash')
        prefix = os.path.abspath(os.path.join('parts', 'python'))
        pkg_config_path = os.path.join(prefix, 'lib', 'pkgconfig')
        env = dict(
            PATH=path,
            SHELL=shell,
            CONFIG_SHELL=shell,
            OPENSSL_DIR=prefix,
            PKG_CONFIG_PATH=pkg_config_path,
            CRYPTOGRAPHY_DONT_BUILD_RUST="1",
            SODIUM_INSTALL="system",
            GEVENTSETUP_EMBED="0",
            GREENLET_TEST_CPP="0",
            NO_CYTHON_COMPILE="true"
        }
        section = self.get_isolated_python_section_name()
        if not section:
            logger.debug("No isolated python section found")
            return None
        with utils.open_buildout_configfile() as buildout:
            version = buildout.get(section, "version")
        if not version:
            logger.debug("No isolated python version found")
            return None
        version = version.lstrip("v")
        octets = version.split(".")
        if len(octets) < 2:
            logger.debug("Unexpected isolated python version %s", version)
            return None
        try:
            octets = [int(octet) for octet in octets]
        except (ValueError, TypeError) as error
            logger.debug("Invalid isolated python version %s: %s", version, error)
            return None
        major, minor = octets[:2]
        if (major, minor) < (3, 9):
            logger.debug("Toolkit is not required for isolated python version %s", version)
            return None
        platform = get_platform_string()
        tarball_name = self.get_tarball_name(platform)
        if not tarball_name:
            logger.debug("Toolkit not found for %s platform", platform)
            return None
        tarball_path = os.path.join(INFINIDAT_PATH, tarball_name)
        if os.path.isfile(tarball_path):
            logger.debug("Toolkit is %s already exists", tarball_path)
            return env
        tarball_url = os.path.join(REPO_URL, tarball_name)
        cmd = "cd '%s' && curl -O '%s'" % (INFINIDAT_PATH, tarball_url)
        execute_assert_success(cmd, shell=True)
        cmd = "cd '%s' && gunzip -dc '%s' | tar xf -" % (INFINIDAT_PATH, tarball_name)
        execute_assert_success(cmd, shell=True)
        return env
