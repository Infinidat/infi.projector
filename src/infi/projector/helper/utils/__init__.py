from contextlib import contextmanager
from logging import getLogger
import sys
import re
try:
    import configparser
except ImportError:     # Python 2
    import ConfigParser as configparser

logger = getLogger(__name__)

BUILDOUT_PARAMETERS = []

class PrettyExecutionError(Exception):
    # infi.execute.ExecutionError does print stdout and stderr well, and this is a must when running buildout
    def __init__(self, result):
        encoding = getattr(sys.stdout, 'encoding', None) or 'utf-8'
        stdout = result.get_stdout()
        if stdout is not None:
            stdout = stdout.decode(encoding)
        stderr = result.get_stderr()
        if stderr is not None:
            stderr = stderr.decode(encoding)
        msg = "Execution of %r failed!\nresult=%s\nstdout=%s\nstderr=%s"
        msg = msg % (result._command, result.get_returncode(), stdout, stderr)
        super(PrettyExecutionError, self).__init__(msg)
        self.result = result

def _chdir_and_log(path):
    from os import chdir
    chdir(path)
    logger.debug("Changed directory to {!r}".format(path))

@contextmanager
def chdir(path):
    from os.path import abspath
    from os import curdir
    path = abspath(path)
    current_dir = abspath(curdir)
    _chdir_and_log(path)
    try:
        yield
    finally:
        _chdir_and_log(current_dir)

@contextmanager
def open_buildout_configfile(filepath="buildout.cfg", write_on_exit=False):
    parser = configparser.ConfigParser()
    parser.optionxform = str    # make options case-sensitive
    parser.read(filepath)
    try:
        yield parser
    finally:
        if not write_on_exit:
            return
        with open(filepath, 'w') as fd:
            parser.write(fd)

def is_running_inside_virtualenv():
    import sys
    from six import string_types
    return isinstance(getattr(sys, 'real_prefix', None), string_types)

def parse_args(commandline_or_args):
    return commandline_or_args if isinstance(commandline_or_args, list) else commandline_or_args.split()

def execute_assert_success(args, env=None):
    from infi import execute
    logger.info("Executing {}".format(' '.join(args)))
    result = execute.execute(args, env=env)
    if result.get_returncode() is not None and result.get_returncode() != 0:
        logger.error(result.get_stderr())
        raise PrettyExecutionError(result)

def _get_executable_from_shebang_line():  # pragma: no cover
    # The executable wrapper in distribute dynamically loads Python's DLL, which causes sys.executable to be the wrapper
    # and not the original python exeuctable. We have to find the real executable as Distribute does.
    from os import path
    import sys
    executable_script_py = sys.executable.replace(".exe", "-script.py")
    if not path.exists(executable_script_py):
        # using original Python executable
        return sys.executable
    with open(executable_script_py) as fd:
        shebang_line = fd.readlines()[0].strip()
    executable_path = path.normpath(shebang_line[2:])
    return (executable_path + '.exe') if not executable_path.endswith('.exe') else executable_path


def get_python_interpreter():
    import os
    import sys
    from ..assertions import is_windows
    if is_windows():
        return _get_executable_from_shebang_line()
    else:
        return os.path.join(sys.real_prefix, 'bin', 'python') if is_running_inside_virtualenv() else sys.executable


def get_executable(filename):
    import os
    dirpath, basename = os.path.split(get_python_interpreter())
    isolated_python_bin = os.path.join('parts', 'python', 'bin')
    filename_with_ext = (filename + '.exe') if basename.endswith('.exe') else filename
    # if we are under a buildout project, the scripts won't be inside the isolated python
    bin_dir = dirpath.replace(isolated_python_bin, 'bin') if \
              dirpath.endswith(isolated_python_bin) else dirpath
    if os.name == 'nt' and 'python' not in filename:
        # if we are write_on_exit windows, the console scripts are under Scripts
        for base_dir in [bin_dir, os.path.abspath(os.path.join(bin_dir, os.pardir))]:
            if os.path.exists(os.path.join(base_dir, 'Scripts')):
                bin_dir = os.path.join(base_dir, 'Scripts')
    return os.path.join(bin_dir, filename_with_ext)


def execute_with_python(commandline_or_args):
    import os
    import sys
    from ..assertions import is_windows
    args = parse_args(commandline_or_args)
    executable = [get_python_interpreter()]
    if not is_running_inside_virtualenv():
        executable.append('-S')
    try:
        execute_assert_success(executable + args)
    except PrettyExecutionError:
        if '-S' not in executable:
            raise
        logger.warning("Command failed with -S, trying without")
        executable.remove('-S')
        execute_assert_success(executable + args)


def get_isolated_executable(filename):
    import os
    from ..assertions import is_windows
    return os.path.join('parts', 'python',
                        'Scripts' if is_windows() and 'python' not in filename else 'bin',
                        '{}{}'.format(filename, '.exe' if is_windows() else ''))


def execute_with_isolated_python(commandline_or_args):
    import os
    from ..assertions import is_windows
    args = parse_args(commandline_or_args)
    executable = [get_isolated_executable('python')]
    with open_buildout_configfile() as buildout:
        if buildout.get('buildout', 'relative-paths') in ['True', 'true']:
            [executable] = os.path.abspath(executable[0])
    execute_assert_success(executable + args)

def execute_with_buildout(commandline_or_args, env=None, stripped=True):
    from os import name, path, environ
    _env = environ.copy()
    if env:
        _env.update(env)
    args = parse_args(commandline_or_args)
    python = path.join('bin', 'python{}'.format('.exe' if name == 'nt' else ''))
    buildout = path.join('bin', 'buildout{}'.format('.exe' if name == 'nt' else ''))
    buildout_script = path.join('bin', 'buildout{}'.format('-script.py' if name == 'nt' else ''))
    if path.exists(python) and not stripped:
        execute_assert_success([python, buildout_script] + BUILDOUT_PARAMETERS + args, env=_env)
    else:
        execute_assert_success([buildout] + BUILDOUT_PARAMETERS + args, env=_env)

@contextmanager
def buildout_parameters_context(parameters):
    try:
        [BUILDOUT_PARAMETERS.append(param) for param in parameters if param not in BUILDOUT_PARAMETERS]
        yield
    finally:
        [BUILDOUT_PARAMETERS.remove(param) for param in parameters if param in BUILDOUT_PARAMETERS]

def _release_version_in_git(version_tag):
    from infi.execute import execute_assert_success
    execute_assert_success("git checkout master", shell=True)
    execute_assert_success("git merge develop --no-ff -m \"Finished Release {}\"".format(version_tag), shell=True)
    execute_assert_success("git tag -a {0} -m {0}".format(version_tag), shell=True)
    execute_assert_success("git checkout develop", shell=True)
    execute_assert_success("git merge master", shell=True)

def git_checkout(branch_name_or_tag):
    from os import curdir
    from gitpy import LocalRepository
    logger.info("checking out '{}'".format(branch_name_or_tag))
    try:
        LocalRepository(curdir).checkout(branch_name_or_tag)
    except Exception:  # pragma: no cover
        logger.error("failed to checkout {}".format(branch_name_or_tag))
        raise SystemExit(1)

def commit_changes_to_buildout(message):
    import os
    from gitpy import LocalRepository
    repository = LocalRepository(os.curdir)
    # workaround https://github.com/msysgit/git/issues/79
    os.system("git status")
    if "buildout.cfg" not in [modified_file.filename for modified_file in repository.getChangedFiles()]:
        return
    repository.add("buildout.cfg")
    repository.commit("buildout.cfg: " + message)

def commit_changes_to_manifest_in(message):
    from os import curdir
    from gitpy import LocalRepository
    repository = LocalRepository(curdir)
    repository.add("MANIFEST.in")
    repository.commit("MANIFEST.in: " + message)

def get_latest_version():
    from os import curdir
    from gitpy import LocalRepository
    from pkg_resources import parse_version
    repository = LocalRepository(curdir)
    version_tags = [tag.name for tag in repository.getTags()
                    if tag.name.startswith('v') and not tag.name.endswith('-develop')]
    version_tags.sort(key=lambda ver: parse_version(ver))
    return version_tags[-1]

@contextmanager
def open_tempfile():
    from tempfile import mkstemp
    from os import close, remove
    fd, path = mkstemp()
    close(fd)
    try:
        yield path
    finally:
        try:
            remove(path)
        except:
            pass

def normalize(name):
    return re.sub(r"[-_.]+", "-", name).lower()

def set_freezed_versions_in_install_requires(buildout_cfg, versions_cfg):
    from .package_sets import InstallRequiresPackageSet, VersionSectionSet, from_dict, to_dict
    install_requires = to_dict(InstallRequiresPackageSet.from_value(buildout_cfg.get("project", "install_requires")))
    versions = to_dict(set([item.replace('==', ">=") for item in VersionSectionSet.from_value(versions_cfg)]))
    for key, value in versions.items():
        if key in install_requires and not install_requires[key]:  # empty list
            install_requires[key] = value
        else:
            for item in install_requires.items():
                if normalize(item[0]) == normalize(key) and not item[1]:
                    install_requires[item[0]] = value
                    break
    install_requires = from_dict(install_requires)
    buildout_cfg.set("project", "install_requires", InstallRequiresPackageSet.to_value(install_requires))

def freeze_versions(versions_file, change_install_requires):
    dependencies = dict()
    with open_buildout_configfile(write_on_exit=True) as buildout_cfg:
        with open_buildout_configfile(versions_file) as versions_cfg:
            if buildout_cfg.has_section("versions"):
                buildout_cfg.remove_section("versions")
            buildout_cfg.add_section("versions")
            for option in sorted(versions_cfg.options("versions"), key=lambda s: s.lower()):
                dependencies[option] = versions_cfg.get("versions", option)
        dependencies.update(**get_dependencies_with_specific_versions(buildout_cfg))
        for key in sorted(dependencies, key=lambda s: s.lower()):
            buildout_cfg.set("versions", key, dependencies[key])
        if change_install_requires:
                set_freezed_versions_in_install_requires(buildout_cfg, versions_cfg)

def unset_freezed_versions_in_install_requires(buildout_cfg):
    from .package_sets import InstallRequiresPackageSet, to_dict, from_dict
    install_requires = InstallRequiresPackageSet.from_value(buildout_cfg.get("project", "install_requires"))
    install_requires_dict = to_dict(install_requires)
    install_requires_dict.update({key: [] for key, specs in install_requires_dict.items()
                                  if specs and specs[-1][0] == '>='})
    install_requires = from_dict(install_requires_dict)
    buildout_cfg.set("project", "install_requires", InstallRequiresPackageSet.to_value(install_requires))


def get_dependencies_with_specific_versions(buildout_cfg):
    from .package_sets import InstallRequiresPackageSet, EggsPackageSet, to_dict
    results = {}
    install_requires = InstallRequiresPackageSet.from_value(buildout_cfg.get("project", "install_requires"))
    install_requires_dict = to_dict(install_requires)
    for key, specs in install_requires_dict.items():
        if specs and len(specs) == 1 and specs[0][0] == '==':
            results[key] = specs[0][1]

    development_eggs = [item for
                        item in EggsPackageSet.from_value(buildout_cfg.get('development-scripts', 'eggs')) if
                        item != '${project:name}']
    development_eggs_dict = to_dict(development_eggs)
    for key, specs in development_eggs_dict.items():
        if specs and len(specs) == 1 and specs[0][0] == '==':
            results[key] = specs[0][1]

    return results


def unfreeze_versions(change_install_requires):
    with open_buildout_configfile(write_on_exit=True) as buildout_cfg:
        buildout_cfg.remove_section("versions")

        dependencies_that_need_to_remain_frozen = get_dependencies_with_specific_versions(buildout_cfg)
        if dependencies_that_need_to_remain_frozen:
            buildout_cfg.add_section("versions")
            for key, value in dependencies_that_need_to_remain_frozen.items():
                buildout_cfg.set("versions", key, value)
        if change_install_requires:
            unset_freezed_versions_in_install_requires(buildout_cfg)


class RevertIfFailedOperations(object):
    def __init__(self, repository):
        super(RevertIfFailedOperations, self).__init__()
        self.repository = repository

    def get_tags(self):
        return {tag.name: tag for tag in self.repository.getTags()}

    def get_branches(self):
        return {branch.name: branch for branch in self.repository.getBranches()}

    def get_head(self, branch_name):
        return self.repository.getBranchByName(branch_name).getHead()

    def get_status(self):
        return dict(develop=self.get_head("develop"), master=self.get_head("master"),
                    tags=self.get_tags(), branches=self.get_branches())

    def delete_new_tags(self, before, now):
        for tag in set(now['tags']).difference(set(before['tags'])):
            cmd = "git tag -d {0}".format(now['tags'][tag].name)
            self.repository._executeGitCommandAssertSuccess(cmd)

    def delete_new_branches(self, before, now):
        for branch in set(now['branches']).difference(set(before['branches'])):
            cmd = "git branch -D {0}".format(now['branches'][branch].name)
            self.repository._executeGitCommandAssertSuccess(cmd)

    def reset_master_and_develop(self, before, now):
        for branch_name in ['master', 'develop']:
            self.repository.resetHard()
            branch = self.repository.getBranchByName(branch_name)
            self.repository.checkout(branch)
            self.repository.resetHard(before[branch_name])

@contextmanager
def revert_if_failed(keep_leftovers):
    from gitpy import LocalRepository
    from os import curdir
    repository = LocalRepository(curdir)
    ops = RevertIfFailedOperations(repository)
    before = ops.get_status()
    try:
        yield
    except:
        if keep_leftovers:
            raise
        repository.checkout('develop')
        now = ops.get_status()
        ops.delete_new_tags(before, now)
        ops.delete_new_branches(before, now)
        ops.reset_master_and_develop(before, now)
        raise

def release_version_in_git(version_tag, keep_leftovers=True):
    with revert_if_failed(keep_leftovers):
        _release_version_in_git(version_tag)
