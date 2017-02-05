from contextlib import contextmanager
from infi.projector.plugins import CommandPlugin
from infi.projector.helper.utils import configparser
from logging import getLogger

logger = getLogger(__name__)

USAGE = """
Usage:
    projector repository init [--mkdir] <project_name> <origin> <short_description> <long_description>
    projector repository clone <origin> [<local-path>]
    projector repository skeleton update [--remove-deprecated-files] [--commit-changes]

Options:
    repository init                 Create a new project/git repository
    repository clone                Clone an exisiting project/git repository
    repository skeleton update      Update skeleton-related files (e.g bootstrap.py)
    <project_name>                  The name of the project in python-module-style (object)
    <origin>                        Remote repository url
    <short_description>             A one-line description
    <long_description>              A multi-line description
    <local-path>                    If missing, the local path will be the project name
    --mkdir                         Init the repository in a new directory instead of the current directory
    --remove-deprecated-files       Remove files that were in use in previous versions of projector but are no longer necessary
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
    try:
        return original.get(section, key)
    except configparser.NoOptionError:
        return default


class RepositoryPlugin(CommandPlugin):
    def get_docopt_string(self):
        return USAGE

    def get_command_name(self):
        return 'repository'

    def get_methods(self):
        return [self.init, self.clone, self.skeleton]

    def get_project_name(self):
        return self.arguments.get("<project_name>")

    @contextmanager
    def _create_subdir_if_necessary(self):
        from infi.projector.helper.utils import chdir
        from os.path import exists, isdir, sep
        from os import makedirs, name, listdir, removedirs
        if not self.arguments.get('--mkdir'):
            yield
            return
        dirname = self.arguments.get('<local-path>') or \
            self.arguments.get('<project_name>') or self.arguments.get('<origin>')
        if name == 'nt':
            dirname = dirname.replace(sep, '/')
        dirname = (dirname if not dirname.endswith('.git') else dirname[0:-4]).split('/')[-1]
        if exists(dirname) and isdir(dirname):
            logger.debug("{} already exists".format(dirname))
            raise SystemExit(1)
        makedirs(dirname)
        try:
            with chdir(dirname):
                yield
        finally:
            if not listdir(dirname):
                removedirs(dirname)

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

    def release_initial_version(self):
        from infi.projector.helper.utils import release_version_in_git
        release_version_in_git("v0")

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
            buildout.set('project', 'namespace_packages', str(get_package_namespace(project_name)))
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
            fd.write("get-pip.py\n")

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

    def init_branches(self):
        from infi.execute import execute_assert_success
        from os import curdir
        from gitpy import LocalRepository
        repository = LocalRepository(curdir)
        branches = [branch.name for branch in repository.getBranches()]
        remotes = repository.getRemotes()
        remote_branches = []
        if len(remotes) > 0:
            remote_branches = [branch.name for branch in remotes[0].getBranches()]
        if 'master' not in branches:
            if 'master' in remote_branches:
                execute_assert_success("git branch --track master origin/master", shell=True)
            else:
                execute_assert_success("git symbolic-ref HEAD refs/heads/master", shell=True)
                execute_assert_success("git commit --allow-empty -m \"Initial commit\"", shell=True)
        if 'develop' not in branches:
            if 'develop' in remote_branches:
                execute_assert_success("git branch --track develop origin/develop", shell=True)
            else:
                execute_assert_success("git branch --no-track develop master", shell=True)

    def init(self):
        with self._create_subdir_if_necessary():
            self._exit_if_dotgit_exists()
            self.git_init()
            self.init_branches()
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
                self.init_branches()

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
                                                   "buildout.in",
                                                   "bootstrap.py"]
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
                backup[section] = {key: get(original, section, key, DEFAULTS.get(key, None))
                                   for key in ATTRIBURES_BY_SECTION[section]}
            logger.info("Writing skeleton files")
            self.overwrite_update_files()
            self.safe_append_to_gitignore("get-pip.py")
            if self.arguments.get("--remove-deprecated-files", False):
                logger.info("Removing deprecated files")
                self.remove_deprecated_files()
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
