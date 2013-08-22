from infi.pyutils.contexts import contextmanager
from infi.projector.plugins import CommandPlugin
from textwrap import dedent
from logging import getLogger

logger = getLogger(__name__)

USAGE = """
Usage:
    projector repository init [--mkdir] <project_name> <origin> <short_description> <long_description>
    projector repository clone <origin>
    projector repository skeleton update [--remove-deprecated-files] [--commit-changes]
    projector repository sync <remote-user> <remote-host> [<remote-path>] [--watch] [--verbose]

Options:
    repository init                 Create a new project/git repository
    repository clone                Clone an exisiting project/git repository
    repository skeleton update      Update skeleton-related files (e.g bootstrap.py)
    repository sync                 sync this repository with a remote target
    <project_name>                  The name of the project in python-module-style (object)
    <origin>                        Remote repository url
    <short_description>             A one-line description
    <long_description>              A multi-line description
    <remote-path>                   if missing, assuming target is at the default installation directory
    --mkdir                         Init the repository in a new directory instead of the current directory
    --remove-deprecated-files       remove files that were in use in previous versions of projector but are no longer necessary
    --watch                         watch for changes
"""


def get_package_namespace(name):
    namespaces = []
    for item in name.split('.')[:-1]:
        namespaces.append('.'.join([namespaces[-1], item]) if namespaces else item)
    return namespaces


def generate_package_code():
    from uuid import uuid1
    return '{' + str(uuid1()) + '}'


def indent(text):
    return '\n'.join(['\t{}'.format(line) for line in text.splitlines()]).strip()


def get(original, section, key, default=None):
    from ConfigParser import NoOptionError
    try:
        return original.get(section, key)
    except NoOptionError:
        return default


class RepositoryPlugin(CommandPlugin):
    def get_docopt_string(self):
        return USAGE

    def get_command_name(self):
        return 'repository'

    def parse_commandline_arguments(self, arguments):
        methods = [self.init, self.clone, self.skeleton, self.sync]
        [method] = [method for method in methods
                    if arguments.get(method.__name__)]
        self.arguments = arguments
        method()

    def get_project_name(self):
        return self.arguments.get("<project_name>")

    @contextmanager
    def _create_subdir_if_necessary(self):
        from infi.projector.helper.utils import chdir
        from os.path import exists, isdir, sep
        from os import makedirs, name
        if not self.arguments.get('--mkdir'):
            yield
            return
        dirname = self.arguments.get('<project_name>') or self.arguments.get('<origin>')
        if name == 'nt':
            dirname = dirname.replace(sep, '/')
        dirname = (dirname if not dirname.endswith('.git') else dirname[0:-4]).split('/')[-1]
        if exists(dirname) and isdir(dirname):
            logger.debug("{} already exists".format(dirname))
            raise SystemExit(1)
        makedirs(dirname)
        with chdir(dirname):
            yield

    def _exit_if_dotgit_exists(self):
        from os.path import exists
        if exists('.git'):
            logger.error("This directory is already a git repository")
            raise SystemExit(1)

    def git_init(self):
        from os.path import curdir
        from gitpy.repository import LocalRepository
        repository = LocalRepository(curdir)
        repository.init()
        repository.addRemote("origin", self.arguments.get('<origin>'))

    def gitflow_init(self):
        from gitflow.core import GitFlow
        gitflow = GitFlow()
        gitflow.init(force_defaults=True)

    def release_initial_version(self):
        from infi.projector.helper.utils import release_version_with_git_flow
        release_version_with_git_flow("v0")

    def add_initial_files(self):
        from os.path import basename
        from shutil import copy
        from .skeleton import get_files
        for src, dst in [(filepath, basename(filepath)) for filepath in get_files()]:
            copy(src, dst)

    def set_buildout_config(self):
        from infi.projector.helper.utils import open_buildout_configfile
        project_name = self.get_project_name()
        with open_buildout_configfile(write_on_exit=True) as buildout:
            buildout.set('project', 'name', project_name)
            buildout.set('project', 'namespace_packages', get_package_namespace(project_name))
            buildout.set('project', 'version_file',
                             '/'.join(['src'] + project_name.split('.') + ['__version__.py']))
            buildout.set('project', 'description', self.arguments.get("<short_description>"))
            buildout.set('project', 'long_description', indent(self.arguments.get("<long_description>")))
            buildout.set('project', 'upgrade_code', generate_package_code())
            buildout.set('project', 'product_name', project_name)

    def get_package_directories(self):
        from os.path import sep
        name = self.get_project_name()
        return [item.replace('.', sep) for item in get_package_namespace(name)] + [name.replace('.', sep)]

    def generate_src(self):
        from os import mkdir
        from os.path import join
        file_content = """__import__("pkg_resources").declare_namespace(__name__)\n"""
        mkdir('src')
        for dirname in self.get_package_directories():
            mkdir(join('src', dirname))
            with open(join('src', dirname, '__init__.py'), 'w') as file:
                file.write(file_content)

    def append_to_gitignore(self):
        project_name = self.get_project_name()
        with open('.gitignore', 'a') as fd:
            fd.write('\n' + '/'.join(['src'] + project_name.split('.') + ['__version__.py']) + '\n')
            fd.write("bootstrap.py\n")

    def safe_append_to_gitignore(self, entry):
        with open('.gitignore') as fd:
            entries = [line.strip() for line in fd.readlines()]
        if entry in entries:
            return
        with open('.gitignore', 'a') as fd:
            fd.write(entry + "\n")

    def commit_all(self):
        from os import curdir
        from gitpy import LocalRepository
        repository = LocalRepository(curdir)
        repository.addAll()
        repository.commit("added all project files")

    def git_checkout_develop(self):
        from os import curdir
        from gitpy import LocalRepository
        repository = LocalRepository(curdir)
        repository.checkout("develop")

    def init(self):
        with self._create_subdir_if_necessary():
            self._exit_if_dotgit_exists()
            self.git_init()
            self.gitflow_init()
            self.release_initial_version()
            self.git_checkout_develop()
            self.add_initial_files()
            self.set_buildout_config()
            self.generate_src()
            self.append_to_gitignore()
            self.commit_all()

    def git_clone(self):
        from os import curdir
        from gitpy import LocalRepository
        repository = LocalRepository(curdir)
        origin = self.arguments.get("<origin>")
        logger.debug("Cloning {}".format(origin))
        repository.clone(origin)

    def origin_has_develop_branch(self):
        from os import curdir
        from gitpy import LocalRepository
        from gitpy.exceptions import NonexistentRefException
        repository = LocalRepository(curdir)
        try:
            repository.getRemoteByName("origin").getBranchByName("develop")
            return True
        except NonexistentRefException:
            return False

    def clone(self):
        self.arguments['--mkdir'] = True
        with self._create_subdir_if_necessary():
            self.git_clone()
            if self.origin_has_develop_branch():
                self.git_checkout_develop()
                self.gitflow_init()

    def overwrite_update_files(self):
        from os.path import basename
        from .skeleton import get_files_to_update
        from shutil import copy
        from os import curdir
        from gitpy import LocalRepository
        repository = LocalRepository(curdir)
        for src, dst in [(filepath, basename(filepath)) for filepath in get_files_to_update()]:
            copy(src, dst)
            logger.info("overwriting {}".format(dst))
            if self.arguments.get("--commit-changes", False):
                repository.add(dst)

    def remove_deprecated_files(self):
        from os import curdir, path, remove
        from gitpy import LocalRepository
        repository = LocalRepository(curdir)
        for filename in [filename for filename in ["buildout-git.cfg",
                                                   "buildout-version.cfg",
                                                   "buildout-pack.cfg",
                                                   "buildout-dist.cfg",
                                                   "buildout.in"]
                         if path.exists(filename)]:
            logger.info("removing {}".format(filename))
            if self.arguments.get("--commit-changes", False):
                repository.delete(filename, force=True)
            else:
                remove(filename)

    def skeleton(self):
        ATTRIBURES_BY_SECTION = {'project': ['name', 'namespace_packages', 'install_requires', 'version_file',
                                             'description', 'long_description', 'console_scripts', 'upgrade_code',
                                             'package_data']}
        DEFAULTS = {'namespace_packages': [], 'install_requires': [], 'console_scripts': [], 'package_data': []}
        from infi.projector.helper.utils import open_buildout_configfile
        if not self.arguments.get("update"):
            logger.error("Not implemented")
            raise SystemExit(1)
        logger.info("Starting skeleton update")
        with open_buildout_configfile() as original:
            backup = {}
            logger.info("Backing up buildout sections")
            for section in ATTRIBURES_BY_SECTION.keys():
                backup[section] = {key:get(original, section, key, DEFAULTS.get(key, None))
                                   for key in ATTRIBURES_BY_SECTION[section]}
            if self.arguments.get("--remove-deprecated-files", False):
                logger.info("Removing deprecated files")
                self.remove_deprecated_files()
            logger.info("Writing skeleton files")
            self.overwrite_update_files()
            self.safe_append_to_gitignore("bootstrap.py")
            with open_buildout_configfile(write_on_exit=True) as update:
                logger.info("Writing buildout.cfg")
                for section, attributes in backup.items():
                    for key, value in attributes.items():
                        update.set(section, key, value)

        if self.arguments.get("--commit-changes", False):
            logger.info("Committing changes")
            from gitpy import LocalRepository
            from os import curdir
            repository = LocalRepository(curdir)
            message = "updated project files from skeleton"
            repository.commit(message, commitAll=True)

    def _get_default_remote_path(self):
        from infi.projector.helper.utils import open_buildout_configfile
        is_windows = self.arguments.get("<remote-user>") == "Administrator"
        basedir = "/cygdrive/c/Program Files/" if is_windows else "/opt"
        with open_buildout_configfile() as buildout:
            get = buildout.get
            if is_windows:
                return "/".join([basedir, get("project", "company"), get("project", "product_name")])
            else:
                return "/".join([basedir, get("project", "company").lower(),
                                 get("project", "product_name").replace(' ', '-').replace('_', '-').lower()])

    def sync(self):
        from infi.pysync import main
        args = ["--python"]
        if self.arguments.get("--watch"):
            args.extend(["--watch"])
        if self.arguments.get("--verbose"):
            args.extend(["--verbose"])
        patterns = [".cache", ".git", ".gitignore", ".installed.cfg", ".projector", "MANIFEST.in",
                    "bin", "bootstrap.py", "develop-eggs", "eggs", "parts", "dist", "devlocal", "data", "setup.py",
                    "src/*egg-info", "src/**/__version__.py"]
        if not self.arguments.get("<remote-path>"):
            patterns.extend(["buildout.cfg", "setup.in"])
        args.extend(["--skip-source={}".format(item) for item in patterns])
        args.extend(["--skip-target={}".format(item) for item in patterns])
        default_remote_path = self._get_default_remote_path()
        args.extend(["{}@{}:{}".format(self.arguments.get("<remote-user>"), self.arguments.get("<remote-host>"),
                     self.arguments.get("<remote-path>") or default_remote_path)])
        logger.info("pysync {}".format(" ".join(args)))
        return main(args)
