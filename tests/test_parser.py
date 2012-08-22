from .test_case import TestCase

class TestParser(TestCase):
    def test_help(self):
        with self.assertRaises(SystemExit):
            self.projector("-h")

    def test_version(self):
        self.projector("-v")

