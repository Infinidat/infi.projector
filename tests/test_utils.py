from .test_case import TestCase

class UtilsTestCase(TestCase):
    def test_execute_assert_success(self):
        from infi.projector.helper.utils import execute_with_buildout
        from infi.execute import ExecutionError
        try:
            execute_with_buildout(["install", "non-existing-section"])
        except ExecutionError, err:
            self.assertFalse(r"\n" not in str(err))
