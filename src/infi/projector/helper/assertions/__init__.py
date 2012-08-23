from infi.pyutils.decorators import wraps
from os import path, name, curdir

from logging import getLogger
logger = getLogger(__name__)

def is_windows():
    return name == 'nt'

def is_executable_exists(filepath):
    return path.exists("{}.exe".format(filepath) if is_windows() else filepath)

def assert_buildout_executable_exists():
    if not is_executable_exists(path.join("bin", "buildout")):
        logger.error("buildout executable does not exist, run `projector build scripts`")
        raise SystemExit(1)

def assert_setup_py_exists():
    if not path.exists("setup.py"):
        logger.error("setup.py does not exist, run `projector build scripts`")
        raise SystemExit(1)

def assert_buildout_configfile_exists():
    if not path.exists("buildout.cfg"):
        logger.error("buidlout.cfg does not exist, the current directory is not a home of a project")
        raise SystemExit(1)

def assert_git_repository():
    if not path.exists(".git"):
        logger.error("the current directory is not a home of a git repository")
        raise SystemExit(1)

def assert_no_uncommitted_changes():
    from gitpy import LocalRepository
    from os import curdir
    repository = LocalRepository(curdir)
    if repository.getChangedFiles() + repository.getStagedFiles():
        logger.error("There are changes pending commit, cannot continue. please commit or checkout those changes")
        raise SystemExit(1)

def assert_isolated_python_exists():
    if not path.exists(path.join("parts", "python")):
        logger.error("Isolated python is required")
        raise SystemExit(1)

def assert_on_branch(branch_name):
    from gitpy import LocalRepository
    repository = LocalRepository(curdir)
    current_branch = repository.getCurrentBranch()
    if current_branch is None or current_branch.name != branch_name:
        logger.error("not currently on branch {}".format(branch_name))
        raise SystemExit(1)

def is_buildout_executable_using_isolated_python():
    with open(path.join("bin", "buildout-script.py" if is_windows() else "buildout")) as fd:
        content = fd.read()
    python_abspath = "{}/parts/python/bin/python".format(path.abspath(curdir))
    python_relpath = "parts/python/bin/python"
    shebang_lines = ["#!" + '"{}"'.format(python) if is_windows() else '#!' + python
                     for python in [python_relpath, python_abspath]]
    return any([content.startswith(shebang_line) for shebang_line in shebang_lines])

def requires_repository(func):
    @wraps(func)
    def callable(*args, **kwargs):
        assert_buildout_configfile_exists()
        assert_git_repository()
        return func(*args, **kwargs)
    return callable

def requires_built_repository(func):
    @wraps(func)
    def callable(*args, **kwargs):
        assert_buildout_configfile_exists()
        assert_git_repository()
        assert_setup_py_exists()
        return func(*args, **kwargs)
    return callable

def is_version_tag_exists(version_tag):
    from gitpy import LocalRepository
    repository = LocalRepository(curdir)
    version_tag = version_tag if version_tag.startswith('v') else 'v' + version_tag
    return version_tag in [tag.name for tag in repository.getTags()]

def assert_version_tag_for_release(version_tag):
    if is_version_tag_exists(version_tag):
        msg = "Version tag {} already released."
        logger.error(msg.format(version_tag))
        raise SystemExit(1)

def assert_version_tag_for_upload(version_tag):
    if not is_version_tag_exists(version_tag):
        msg = "Version tag {} doesn't exist, cannot upload it."
        logger.error(msg.format(version_tag))
        raise SystemExit(1)

def assert_local_repository_not_behind_origin_on_develop_and_master_branches():
    from gitpy import LocalRepository
    from os import curdir
    repository = LocalRepository(curdir)
    branches = [repository.getBranchByName(branch_name) for branch_name in ['master', 'develop']]
    branches_with_remote = [branch for branch in branches if branch.getRemoteBranch() is not None]
    for branch in branches_with_remote:
        remote_branch = branch.getRemoteBranch()
        if branch.getMergeBase(remote_branch) != remote_branch:
            logger.error("local branch {} is not on top of origin, please rebase".format(branch))
            raise SystemExit(1)

def assert_develop_branch_on_top_of_master():
    from gitpy import LocalRepository
    from os import curdir
    repository = LocalRepository(curdir)
    develop = repository.getBranchByName("develop")
    master = repository.getBranchByName("master")
    if develop.getMergeBase(master) != master:
        logger.error("{} is not on top of {}, please rebase".format(develop, master))
        raise SystemExit(1)
