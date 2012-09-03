from .test_case import TestCase
from infi.unittest.parameters import iterate
from infi.pyutils.contexts import contextmanager
from gitpy import LocalRepository
from os import curdir

RELEASE_TAGS = dict(major='1.0', minor='v0.1', trivial='0.0.1')

class VersionTestCase(TestCase):
    @iterate("version", ['major', 'minor', 'trivial', '0.1', 'v0.1', '0.0.1', '1.0'])
    def test_release__defaults(self, version):
        with self.mock_build_and_upload_distributions():
            with self.temporary_directory_context():
                self.projector("repository init a.b.c none short long")
                self.projector("devenv build --no-scripts --no-readline")
                self.projector("version release --no-fetch {}".format(version))
                self.assert_tag_exists(RELEASE_TAGS.get(version, version))

    def test_release__without_upload(self):
        with self.mock_build_and_upload_distributions() as mock:
            with self.temporary_directory_context():
                mock.side_effect = RuntimeError()
                self.projector("repository init a.b.c none short long")
                self.projector("devenv build --no-scripts --no-readline")
                self.projector("version release 1.2.3 --no-fetch --no-upload")
                self.assert_tag_exists('v1.2.3')

    def test_release__not_on_develop_branch(self):
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            self.projector("devenv build --no-scripts --no-readline")
            repository = LocalRepository(curdir)
            repository.checkout("master")
            with self.assertRaises(SystemExit):
                self.projector("version release 1.2.3 --no-fetch --no-upload")

    def test_release__master_diverged(self):
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            self.projector("devenv build --no-scripts --no-readline")
            repository = LocalRepository(curdir)
            repository.checkout("master")
            repository.commit("empty commit", allowEmpty=True)
            repository.checkout("develop")
            with self.assertRaises(SystemExit):
                self.projector("version release 1.2.3 --no-fetch --no-upload")

    def test_local_behind_origin(self):
        from os import curdir
        from os.path import abspath, basename
        from infi.projector.helper.utils import chdir
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            self.projector("devenv build --no-scripts --no-readline")
            origin = abspath(curdir)
            with self.temporary_directory_context():
                self.projector("repository clone {}".format(origin))
                with chdir(basename(origin)):
                    self.projector("devenv build --no-scripts --no-readline")
                    with chdir(origin):
                        repository = LocalRepository(curdir)
                        repository.checkout("master")
                        repository.commit("empty commit", allowEmpty=True)
                    with self.assertRaises(SystemExit):
                        self.projector("version release 1.2.3 --no-upload")

    def test_local_behind_origin__no_fetch(self):
        from os import curdir
        from os.path import abspath, basename
        from infi.projector.helper.utils import chdir
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            self.projector("devenv build --no-scripts --no-readline")
            origin = abspath(curdir)
            with self.temporary_directory_context():
                self.projector("repository clone {}".format(origin))
                with chdir(basename(origin)):
                    self.projector("devenv build --no-scripts --no-readline")
                    with chdir(origin):
                        repository = LocalRepository(curdir)
                        repository.checkout("master")
                        repository.commit("empty commit", allowEmpty=True)
                    self.projector("version release 1.2.3 --no-fetch --no-upload")

    def test_upload(self):
        from mock import patch
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            self.projector("devenv build --no-script")
            self.projector("version release 1.2.3 --no-fetch --no-upload")
            with patch("infi.projector.helper.utils.execute_with_buildout") as execute_with_buildout:
                self.projector("version upload 1.2.3")
            execute_with_buildout.assert_any_call("setup . register -r pypi sdist upload -r pypi")
            execute_with_buildout.assert_any_call("setup . register -r pypi bdist_egg upload -r pypi")

    def test_release_with_uncommitted_changes(self):
        from mock import patch
        from os import remove, path
        with self.temporary_directory_context():
            self.projector("repository init a.b.c none short long")
            self.projector("devenv build --no-script")
            remove("buildout.cfg")
            with self.assertRaises(SystemExit):
                self.projector("version release 1.2.3 --no-fetch --no-upload")
            self.assertFalse(path.exists("buildout.cfg"))

    @contextmanager
    def mock_build_and_upload_distributions(self):
        from mock import patch
        from infi.projector.plugins.builtins.version import VersionPlugin
        with patch.object(VersionPlugin, "build_and_upload_distributions") as mock:
            yield mock

    def assert_tag_exists(self, tag):
        from infi.projector.helper.assertions import is_version_tag_exists
        self.assertTrue(is_version_tag_exists(tag))