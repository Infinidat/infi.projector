from infi.projector.plugins import CommandPlugin
from infi.projector.helper import assertions
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
    --distributions=DISTRIBUTIONS   Distributions to build [default: sdist,bdist_wheel]
    --pypi-servers=PYPI             PyPI server for publishing (as defined in pypirc file) [default: pypi,]
    --no-push-changes               Do no push release commits and tags to origin
    --keep-leftovers                If something fails during release, don't
"""

class VersionPlugin(CommandPlugin):
    def get_docopt_string(self):
        return USAGE

    def get_command_name(self):
        return 'version'

    def get_methods(self):
        return [self.release, self.upload]

    @assertions.requires_repository
    def pre_command_assertions(self):
        assertions.assert_setup_py_exists()
        assertions.assert_on_branch("develop")
        assertions.assert_no_uncommitted_changes()

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
        return '.'.join([str(item) for item in version_numbers[:2 if placeholder < 2 else 3]])

    def fetch_origin(self):
        from gitpy import LocalRepository
        from gitpy.exceptions import GitCommandFailedException
        from os import curdir
        repository = LocalRepository(curdir)
        try:
            repository.fetch()
        except (TypeError, GitCommandFailedException) as error:
            logger.error("Failed to fetch origin: {}".format(getattr(error, 'msg', error.message)))
            logger.info("Either fix this or run with --no-fetch")
            raise SystemExit(1)

    def release(self):
        from infi.projector.helper import assertions
        from infi.projector.helper.utils import release_version_in_git
        version_tag = self.replace_version_tag()
        if not self.arguments.get('--no-fetch', False):
            self.fetch_origin()
        assertions.assert_version_tag_for_release(version_tag)
        assertions.assert_develop_branch_on_top_of_master()
        assertions.assert_develop_and_master_not_behind_origin()
        version_tag_without_v = version_tag.lstrip('v')
        version_tag_with_v = 'v{}'.format(version_tag_without_v)
        release_version_in_git(version_tag_with_v, self.arguments.get("--keep-leftovers", False))
        self.arguments['<version>'] = version_tag
        push_changes = not self.arguments.get("--no-push-changes", False)
        if push_changes:
            self.push_commits_and_tags()
        if not self.arguments.get('--no-upload', False) and len(self.arguments.get("--pypi-servers")) > 0:
            self.upload()

    def upload(self):
        from infi.projector.helper.assertions import assert_version_tag_for_upload
        from infi.projector.helper.utils import get_latest_version
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

    def push_commits_and_tags(self):
        from infi.execute import execute_assert_success
        logger.debug("Pushing changes to origin")
        execute_assert_success("git push --all", shell=True)
        execute_assert_success("git push --tags", shell=True)

    def get_git_describe(self):
        from infi.execute import execute_assert_success
        return execute_assert_success("git describe --tags", shell=True).get_stdout().splitlines()[0].decode("utf-8")

    def build_and_upload_distributions(self, version_tag_with_v):
        from infi.projector.helper.utils import execute_with_buildout, git_checkout
        from infi.projector.plugins.builtins.devenv import DevEnvPlugin

        with open('setup.py') as fd:
            has_c_extensions = 'ext_modules' in fd.read()

        for distribution in self.arguments.get("--distributions").split(','):
            for pypi in self.arguments.get("--pypi-servers").split(','):
                if not pypi:
                    continue
                git_checkout(version_tag_with_v)
                DevEnvPlugin().create_setup_py()
                setup_cmd = "setup . {distribution} upload -r {pypi} {universal_flag}"
                universal_flag = '--universal' if distribution == 'bdist_wheel' and has_c_extensions else ''
                setup_cmd = setup_cmd.format(pypi=pypi, distribution=distribution, universal_flag=universal_flag).strip()
                execute_with_buildout(setup_cmd, env=dict(LC_ALL="C"))
                git_checkout("develop")

