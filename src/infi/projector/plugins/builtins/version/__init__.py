from contextlib import contextmanager
from infi.projector.plugins import CommandPlugin
from infi.projector.helper import assertions
from textwrap import dedent
from logging import getLogger

logger = getLogger(__name__)

USAGE = """
Usage:
    projector version release <version> [--no-fetch] (--no-upload | [--distributions=DISTRIBUTIONS] [--pypi-servers=PYPI_SERVERS]) [--no-push-changes] [--keep-leftovers]
    projector version upload <version> [--distributions=DISTRIBUTIONS] [--pypi-servers=PYPI_SERVERS]

Options:
    version release                 Release a new version, including registering and uploading to pypi
    version upload                  Upload an exisiting version to pypi
    <version>                       x.y.z, or the keywords: trivial, minor, major ('release' only); current, latest ('upload' only)
    --no-upload                     Do not upload the package as part of the release process
    --no-fetch                      Do not fetch origin before releasing
    --distributions=DISTRIBUTIONS   Distributions to build [default: sdist,bdist_egg]
    --pypi-servers=PYPI             PyPI server for publishing [default: pypi,]
    --no-push-changes               Do no push release commits and tags to origin
    --keep-leftovers                If something fails during release, don't
"""

class VersionPlugin(CommandPlugin):
    def get_docopt_string(self):
        return USAGE

    def get_command_name(self):
        return 'version'

    @assertions.requires_built_repository
    def parse_commandline_arguments(self, arguments):
        assertions.assert_on_branch("develop")
        assertions.assert_no_uncommitted_changes()
        methods = [self.release, self.upload]
        [method] = [method for method in methods
                    if arguments.get(method.__name__)]
        self.arguments = arguments
        method()

    def replace_version_tag(self):
        """find the next major/minor/trivial version number if applicable"""
        version_tag = self.arguments.get('<version>')
        special_keywords = ['current', 'latest']
        if version_tag in special_keywords:
            logger.error("releasing version '{}' is disallowed. Did you mean 'version upload'?".format(version_tag))
            raise SystemExit(1)
        placeholders = dict(major=0, minor=1, trivial=2)
        placeholder = placeholders.get(version_tag)
        if placeholder is None:
            return version_tag
        current_version = self.get_git_describe().lstrip('v')
        version_numbers = current_version.split('-')[0].split('.')
        version_numbers = [int(item) for item in version_numbers]
        version_numbers = version_numbers[:placeholder + 1]
        while len(version_numbers) < 3:
            version_numbers.append(0)
        version_numbers[placeholder] += 1
        return '.'.join([str(item) for item in version_numbers[:2 if placeholder<2 else 3]])

    def fetch_origin(self):
        from gitpy import LocalRepository
        from gitpy.exceptions import GitCommandFailedException
        from os import curdir
        repository = LocalRepository(curdir)
        try:
            repository.fetch()
        except (TypeError, GitCommandFailedException), error:
            logger.error("Failed to fetch origin: {}".format(getattr(error, 'msg', error.message)))
            logger.info("Either fix this or run with --no-fetch")
            raise SystemExit(1)

    def release(self):
        from infi.projector.helper import assertions
        from infi.projector.helper.utils import release_version_with_git_flow, git_checkout
        version_tag = self.replace_version_tag()
        if not self.arguments.get('--no-fetch', False):
            self.fetch_origin()
        assertions.assert_version_tag_for_release(version_tag)
        assertions.assert_develop_branch_on_top_of_master()
        assertions.assert_develop_and_master_not_behind_origin()
        version_tag_without_v = version_tag.lstrip('v')
        version_tag_with_v = 'v{}'.format(version_tag_without_v)
        release_version_with_git_flow(version_tag_with_v, self.arguments.get("--keep-leftovers", False))
        self.arguments['<version>'] = version_tag
        push_changes = not self.arguments.get("--no-push-changes", False)
        if push_changes:
            self.push_commits_and_tags()
        if self.arguments.get('--no-upload', False):
            git_checkout("develop")
        else:
            self.upload()

    def upload(self):
        from infi.projector.helper.assertions import assert_version_tag_for_upload
        from infi.projector.helper.utils import release_version_with_git_flow, git_checkout, get_latest_version
        version_tag = self.arguments['<version>']
        assert_version_tag_for_upload(version_tag)
        if version_tag == 'current':
            version_to_upload = 'HEAD'
        elif version_tag == 'latest':
            version_to_upload = get_latest_version()
        else:
            version_tag_without_v = version_tag.lstrip('v')
            version_to_upload = 'v{}'.format(version_tag_without_v)
        self.build_and_upload_distributions(version_to_upload)
        git_checkout("develop")

    def get_repository(self):
        from gitpy import LocalRepository
        from os import curdir
        return LocalRepository(curdir)

    def push_commits_and_tags(self):
        repository = self.get_repository()
        logger.debug("Pushing changes to origin")
        repository._executeGitCommandAssertSuccess("git push --all")
        repository._executeGitCommandAssertSuccess("git push --tags")

    def get_git_describe(self):
        return self.get_repository()._executeGitCommand("git describe --tags").stdout.read().splitlines()[0]

    def get_current_version_from_git_describe(self):
        returned = self.get_git_describe()
        all_tags = set(tag.name for tag in self.get_repository().getTags())
        if returned not in all_tags:
            returned = "{}.post{}.{}".format(*returned.rsplit("-", 2))
        return returned

    def build_and_upload_distributions(self, version_tag_with_v):
        from infi.projector.helper.utils import execute_with_buildout, git_checkout
        from infi.projector.plugins.builtins.devenv import DevEnvPlugin
        from infi.projector.scripts import projector
        from gitpy import LocalRepository
        from os import curdir
        repository = LocalRepository(curdir)
        for distribution in self.arguments.get("--distributions").split(','):
            for pypi in self.arguments.get("--pypi-servers").split(','):
                git_checkout(version_tag_with_v)
                DevEnvPlugin().create_setup_py()
                setup_cmd = "setup . register -r {pypi} {distribution} upload -r {pypi}"
                setup_cmd = setup_cmd.format(pypi=pypi, distribution=distribution)
                execute_with_buildout(setup_cmd)
