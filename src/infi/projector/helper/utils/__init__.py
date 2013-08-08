
from contextlib import contextmanager
from logging import getLogger
logger = getLogger(__name__)

BUILDOUT_PARAMETERS = []

class PrettyExecutionError(Exception):
    # infi.execute.ExecutionError does print stdout and stderr well, and this is a must when running buildout
    def __init__(self, result):
        super(PrettyExecutionError, self).__init__("Execution of %r failed!\nresult=%s\nstdout=%s\nstderr=%s" % (result._command,
                                                                                                                 result.get_returncode(),
                                                                                                                 result.get_stdout(),
                                                                                                                 result.get_stderr()))
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
    from ConfigParser import ConfigParser
    parser = ConfigParser()
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
    return hasattr(sys, 'real_prefix')

def parse_args(commandline_or_args):
    return commandline_or_args if isinstance(commandline_or_args, list) else commandline_or_args.split()

def execute_assert_success(args):
    from infi import execute
    logger.info("Executing {}".format(' '.join(args)))
    result = execute.execute(args)
    if result.get_returncode() is not None and result.get_returncode() != 0:
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

def execute_with_python(commandline_or_args):
    import sys
    from ..assertions import is_windows
    args = parse_args(commandline_or_args)
    executable = [sys.executable if not is_windows() else _get_executable_from_shebang_line()]
    if not is_running_inside_virtualenv():
        executable.append('-S')
    try:
        execute_assert_success(executable + args)
    except PrettyExecutionError:
        if '-S' not in executable:
            raise
        logger.warning("Command falied with -S, trying without")
        executable.remove('-S')
        execute_assert_success(executable + args)

def execute_with_isolated_python(commandline_or_args):
    import sys
    import os
    from ..assertions import is_windows
    args = parse_args(commandline_or_args)
    executable = [os.path.join('parts', 'python', 'bin', 'python{}'.format('.exe' if is_windows() else ''))]
    with open_buildout_configfile() as buildout:
        if buildout.get('buildout', 'relative-paths') in ['True', 'true']:
            [executable] = os.path.abspath(executable[0])
    execute_assert_success(executable + args)

def execute_with_buildout(commandline_or_args):
    from os import name, path
    args = parse_args(commandline_or_args)
    execute_assert_success([path.join('bin', 'buildout{}'.format('.exe' if name == 'nt' else ''))] + \
                            BUILDOUT_PARAMETERS + args)

@contextmanager
def buildout_parameters_context(parameters):
    try:
        _ = [BUILDOUT_PARAMETERS.append(param) for param in parameters if param not in BUILDOUT_PARAMETERS]
        yield
    finally:
        _ = [BUILDOUT_PARAMETERS.remove(param) for param in parameters if param in BUILDOUT_PARAMETERS]

def _release_version_with_git_flow(version_tag):
    from os import curdir
    from gitflow.core import GitFlow
    from gitpy import LocalRepository
    gitflow = GitFlow()
    gitflow.create("release", version_tag, base=None, fetch=False)
    gitflow.finish("release", version_tag, fetch=False, rebase=False, keep=False, force_delete=True,
                   tagging_info=dict(sign=False, message=version_tag))
    repository = LocalRepository(curdir)

def git_checkout(branch_name_or_tag):
    from os import curdir
    from gitpy import LocalRepository
    logger.info("checking out '{}'".format(branch_name_or_tag))
    try:
        LocalRepository(curdir).checkout(branch_name_or_tag)
    except Exception: # pragma: no cover
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

def set_freezed_versions_in_install_requires(buildout_cfg, versions_cfg):
    from .package_sets import InstallRequiresPackageSet, VersionSectionSet, from_dict, to_dict
    install_requires = to_dict(InstallRequiresPackageSet.from_value(buildout_cfg.get("project", "install_requires")))
    versions = to_dict(set([item.replace('==', ">=") for item in VersionSectionSet.from_value(versions_cfg)]))
    for key, value in versions.items():
        if not install_requires.has_key(key):
            continue
        if not install_requires[key]: # empty list
            install_requires[key] = value
    install_requires = from_dict(install_requires)
    buildout_cfg.set("project", "install_requires", InstallRequiresPackageSet.to_value(install_requires))

def freeze_versions(versions_file, change_install_requires):
    from os import curdir, path
    with open_buildout_configfile(write_on_exit=True) as buildout_cfg:
        with open_buildout_configfile(versions_file) as versions_cfg:
            if not buildout_cfg.has_section("versions"):
                buildout_cfg.add_section("versions")
            for option in buildout_cfg.options("versions"):
                buildout_cfg.remove_option("versions", option)
            for option in versions_cfg.options("versions"):
                buildout_cfg.set("versions", option, versions_cfg.get("versions", option))
        if change_install_requires:
                set_freezed_versions_in_install_requires(buildout_cfg, versions_cfg)

def unset_freezed_versions_in_install_requires(buildout_cfg):
    from .package_sets import InstallRequiresPackageSet, to_dict, from_dict
    install_requires = InstallRequiresPackageSet.from_value(buildout_cfg.get("project", "install_requires"))
    install_requires_dict = to_dict(install_requires)
    install_requires_dict.update({key:[] for key, specs in install_requires_dict.items()
                                  if specs and specs[-1][0] == '>='})
    install_requires = from_dict(install_requires_dict)
    buildout_cfg.set("project", "install_requires", InstallRequiresPackageSet.to_value(install_requires))

def unfreeze_versions(change_install_requires):
    with open_buildout_configfile(write_on_exit=True) as buildout_cfg:
        buildout_cfg.remove_option("buildout", "extensions")
        buildout_cfg.remove_option("buildout", "buildout_versions_file")
        buildout_cfg.remove_option("buildout", "extends")
        buildout_cfg.remove_option("buildout", "versions")
        buildout_cfg.remove_section("versions")
        if change_install_requires:
            unset_freezed_versions_in_install_requires(buildout_cfg)

class RevertIfFailedOperations(object):
    def __init__(self, repository):
        super(RevertIfFailedOperations, self).__init__()
        self.repository = repository

    def get_tags(self):
        return {tag.name:tag for tag in self.repository.getTags()}

    def get_branches(self):
        return {branch.name:branch for branch in self.repository.getBranches()}

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

def release_version_with_git_flow(version_tag, keep_leftovers=True):
    with revert_if_failed(keep_leftovers):
        _release_version_with_git_flow(version_tag)
