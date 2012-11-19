from unittest import SkipTest
from .test_case import TestCase

class UtilsTestCase(TestCase):
    def test_execute_assert_success(self):
        from infi.projector.helper.utils import execute_with_buildout, PrettyExecutionError
        try:
            execute_with_buildout(["install", "non-existing-section"])
        except PrettyExecutionError, err:
            self.assertFalse(r"\n" in str(err))
        except OSError:
            raise SkipTest("bin/buildout not found")

    def test_revert_if_failed(self):
        from infi.projector.helper.utils import revert_if_failed
        from gitpy import LocalRepository
        from os import curdir
        class Messup(Exception):
            pass
        def mess_things_up_and_raise():
            repository = LocalRepository('.')
            repository.commit("message", allowEmpty=True)
            repository.createTag("test-tag")
            repository.createBranch("new-branch")
            raise Messup()
        with self.temporary_directory_context():
            self.projector("repository init test None a b")
            with self.assertRaises(Messup):
                with revert_if_failed(False):
                    mess_things_up_and_raise()
            repository = LocalRepository('.')
            self.assertEquals(2, len(repository.getBranches()))
            self.assertEquals(2, len(repository.getTags()), repository.getTags())
