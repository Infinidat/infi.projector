from unittest import SkipTest
from .test_case import TestCase
from infi.unittest.parameters import iterate
from contextlib import contextmanager
from infi.gitpy import LocalRepository
from os import curdir, name
from mock import patch
from infi.projector.plugins.builtins.version import VersionPlugin

is_windows = name == "nt"

RELEASE_TAGS = dict(major='1.0', minor='v0.1', trivial='0.0.1')

class VersionTestCase(TestCase):
    @iterate("version", ['major', 'minor', 'trivial', '0.1', 'v0.1', '0.0.1', '1.0'])
    def test_release__defaults(self, version):
        with self.mock_build_and_upload_distributions():
            with self.temporary_directory_context():
                self.projector("repository init a.b.c none short long")
                self.projector("devenv build --no-scripts")
                self.projector("version release --no-fetch {} --no-push-changes".format(version))
                self.assert_tag_exists(RELEASE_TAGS.get(version, version))

    def test_release__without_upload(self):
        with self.mock_build_and_upload_distributions() as mock:
            with self.temporary_directory_context():
                mock.side_effect = RuntimeError()
                self.projector("repository init a.b.c none short long")
                self.projector("devenv build --no-scripts")
                self.projector("version release 1.2.3 --no-fetch --no-upload --no-push-changes")
                self.assert_tag_exists('v1.2.3')

    def test_release__not_on_develop_branch(self):
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            self.projector("devenv build --no-scripts")
            repository = LocalRepository(curdir)
            repository.checkout("master")
            with self.assertRaises(SystemExit):
                self.projector("version release 1.2.3 --no-fetch --no-upload --no-push-changes")

    def test_release__master_diverged(self):
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            self.projector("devenv build --no-scripts")
            repository = LocalRepository(curdir)
            repository.checkout("master")
            repository.commit("empty commit", allowEmpty=True)
            repository.checkout("develop")
            with self.assertRaises(SystemExit):
                self.projector("version release 1.2.3 --no-fetch --no-upload --no-push-changes")

    def test_local_behind_origin(self):
        from os import curdir
        from os.path import abspath, basename
        from infi.projector.helper.utils import chdir
        if is_windows:
            raise SkipTest("skipping test on windows")
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            self.projector("devenv build --no-scripts")
            origin = abspath(curdir)
            with self.temporary_directory_context():
                self.projector("repository clone {}".format(origin))
                with chdir(basename(origin)):
                    self.projector("devenv build --no-scripts")
                    with chdir(origin):
                        repository = LocalRepository(curdir)
                        repository.checkout("master")
                        repository.commit("empty commit", allowEmpty=True)
                    with self.assertRaises(SystemExit):
                        self.projector("version release 1.2.3 --no-upload --no-push-changes")

    def test_local_behind_origin__no_fetch(self):
        from os import curdir
        from os.path import abspath, basename
        from infi.projector.helper.utils import chdir
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            self.projector("devenv build --no-scripts")
            origin = abspath(curdir)
            with self.temporary_directory_context():
                self.projector("repository clone {}".format(origin))
                with chdir(basename(origin)):
                    self.projector("devenv build --no-scripts")
                    with chdir(origin):
                        repository = LocalRepository(curdir)
                        repository.checkout("master")
                        repository.commit("empty commit", allowEmpty=True)
                    self.projector("version release 1.2.3 --no-fetch --no-upload  --no-push-changes")

    def test_upload(self):
        from os import path
        import tempfile
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            self.projector("devenv build --no-script")
            self.projector("version release 1.2.3 --no-fetch --no-upload --no-push-changes")
            tmp_dir =  path.join(tempfile.gettempdir(), 'foobar')
            with patch("infi.projector.helper.utils.execute_with_buildout") as execute_with_buildout, \
                                        patch("infi.execute.execute_assert_success", return_value=0) as execute, \
                                        patch("tempfile.mkdtemp", return_value=tmp_dir), patch("shutil.rmtree"):
                self.projector("version upload 1.2.3")
            execute_with_buildout.assert_any_call("setup . sdist --dist-dir={}".format(tmp_dir), env=dict(LC_ALL="C"))
            execute_with_buildout.assert_any_call("setup . bdist_wheel --dist-dir={}".format(tmp_dir),
                                                  env=dict(LC_ALL="C"))
            self.assertTrue(len(execute.call_args_list), 2)
            twine_path = path.join('bin', 'twine')
            for call_args in execute.call_args_list:
                # Ignore twine's path prefix which may vary
                self.assertTrue(call_args[0][0].endswith('{} upload --repository pypi {}'.format(
                                                                                twine_path, path.join(tmp_dir, '*'))))

    def test_release_with_uncommitted_changes(self):
        from mock import patch
        from os import remove, path
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            self.projector("devenv build --no-script")
            remove("buildout.cfg")
            with self.assertRaises(SystemExit):
                self.projector("version release 1.2.3 --no-fetch --no-upload --no-push-changes")
            self.assertFalse(path.exists("buildout.cfg"))

    @contextmanager
    def mock_build_and_upload_distributions(self):
        from mock import patch
        with patch.object(VersionPlugin, "build_and_upload_distributions") as mock:
            yield mock

    def assert_tag_exists(self, tag):
        from infi.projector.helper.assertions import is_version_tag_exists
        self.assertTrue(is_version_tag_exists(tag))

    def test_release_with_push(self):
        from infi.projector.helper.utils import chdir
        from os import path, curdir
        from infi.gitpy import LocalRepository
        with self.mock_build_and_upload_distributions():
            with self.temporary_directory_context() as origin_location:
                self.projector("repository init a.b.c none short long")
                self.projector("devenv build --no-scripts")
                self.projector("version release minor --no-fetch --pypi-servers= --no-push-changes")
                git_config = path.join(".git", "config")
                LocalRepository(curdir)._executeGitCommandAssertSuccess("git config -f {} receive.denyCurrentBranch ignore".format(git_config))
                with self.temporary_directory_context():
                    self.projector("repository clone {}".format(origin_location))
                    with chdir(path.basename(origin_location)):
                        self.projector("devenv build --no-scripts")
                        self.projector("version release minor --pypi-servers=")

    def test_reset_minor_when_releasing_major(self):
        with patch.object(VersionPlugin, "get_git_describe", return_value="2.5.0"):
            plugin = VersionPlugin()
            plugin.arguments = {"<version>": "major"}
            result = plugin.replace_version_tag()
            self.assertEqual(result, "3.0")

    def test_reset_trivial_when_releasing_major(self):
        with patch.object(VersionPlugin, "get_git_describe", return_value="0.0.5"):
            plugin = VersionPlugin()
            plugin.arguments = {"<version>": "major"}
            result = plugin.replace_version_tag()
            self.assertEqual(result, "1.0")

    def test_reset_trivial_when_releasing_minor(self):
        with patch.object(VersionPlugin, "get_git_describe", return_value="1.5.5"):
            plugin = VersionPlugin()
            plugin.arguments = {"<version>": "minor"}
            result = plugin.replace_version_tag()
            self.assertEqual(result, "1.6")
