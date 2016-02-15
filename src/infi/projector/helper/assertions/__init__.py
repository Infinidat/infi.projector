from os import path, name, curdir
from gitpy import LocalRepository

from logging import getLogger
logger = getLogger(__name__)

def is_windows():
    return name == 'nt'

def is_executable_exists(filepath):
    return path.exists("{}.exe".format(filepath) if is_windows() else filepath)

def assert_buildout_executable_exists():
    if not is_executable_exists(path.join("bin", "buildout")):
        logger.error("buildout executable does not exist, run `projector devenv build`")
        raise SystemExit(1)

def assert_setup_py_exists():
    if not path.exists("setup.py"):
        logger.error("setup.py does not exist, run `projector devenv build`")
        raise SystemExit(1)

def assert_buildout_configfile_exists():
    if not path.exists("buildout.cfg"):
        logger.error("buildout.cfg does not exist, the current directory is not a home of a project")
        raise SystemExit(1)

def assert_git_repository():
    if not path.exists(".git"):
        logger.error("the current directory is not a home of a git repository")
        raise SystemExit(1)

def assert_no_uncommitted_changes():
    repository = LocalRepository(curdir)
    changes = repository.getChangedFiles() + repository.getStagedFiles()
    if changes:
        message = "There are changes pending commit, cannot continue. please commit or stash them:\n"
        logger.error(message+repr(changes))
        raise SystemExit(1)

def is_isolated_python_exists():
    return path.exists(path.join("parts", "python", "bin",
                                 "python{}".format('.exe' if is_windows() else '')))

def assert_isolated_python_exists():
    if not is_isolated_python_exists():
        logger.error("Isolated python is required")
        raise SystemExit(1)

def assert_on_branch(branch_name):
    repository = LocalRepository(curdir)
    current_branch = repository.getCurrentBranch()
    if current_branch is None or current_branch.name != branch_name:
        logger.error("not currently on branch {}".format(branch_name))
        raise SystemExit(1)

def is_executable_using_isolated_python(executable_name):
    filepath = path.join("bin", "{}-script.py".format(executable_name) if is_windows() else executable_name)
    with open(filepath) as fd:
        content = fd.read()
    logger.debug("{}:\n{}".format(filepath, content))
    python_relpath = path.normpath("parts/python/bin/python")
    first_line = content.splitlines()[0]
    return first_line.startswith("#!") and python_relpath in first_line

def is_buildout_executable_using_isolated_python():
    return is_executable_using_isolated_python("buildout")

def requires_repository(func):
    def decorator(*args, **kwargs):
        assert_buildout_configfile_exists()
        assert_git_repository()
        return func(*args, **kwargs)
    return decorator

def is_version_tag_exists(version_tag):
    repository = LocalRepository(curdir)
    version_tag = version_tag if version_tag.startswith('v') else 'v' + version_tag
    return version_tag in [tag.name for tag in repository.getTags()]

def assert_version_tag_for_release(version_tag):
    if is_version_tag_exists(version_tag):
        msg = "Version tag {} already released."
        logger.error(msg.format(version_tag))
        raise SystemExit(1)

def assert_version_tag_for_upload(version_tag):
    if all([not is_version_tag_exists(version_tag), version_tag not in ['current', 'latest']]):
        msg = "Version tag {} doesn't exist, cannot upload it."
        logger.error(msg.format(version_tag))
        raise SystemExit(1)

def assert_develop_and_master_not_behind_origin():
    repository = LocalRepository(curdir)
    branches = [repository.getBranchByName(branch_name) for branch_name in ['master', 'develop']]
    branches_with_remote = [branch for branch in branches if branch.getRemoteBranch() is not None]
    for branch in branches_with_remote:
        remote_branch = branch.getRemoteBranch()
        if branch.getMergeBase(remote_branch) != remote_branch:
            logger.error("local branch {} is not on top of origin, please rebase".format(branch))
            raise SystemExit(1)

def assert_develop_branch_on_top_of_master():
    repository = LocalRepository(curdir)
    develop = repository.getBranchByName("develop")
    master = repository.getBranchByName("master")
    if develop.getMergeBase(master) != master:
        logger.error("{} is not on top of {}, please rebase".format(develop, master))
        raise SystemExit(1)
