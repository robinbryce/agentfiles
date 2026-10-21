"""Guards against test-harness mistakes that make a suite silently green."""
import importlib
import pkgutil
import unittest

import tests
from .base import WifCase

RESERVED = {"run", "setUp", "tearDown", "id", "debug", "countTestCases", "defaultTestResult",
            "shortDescription", "subTest", "skipTest", "addCleanup", "doCleanups", "enterContext"}


class HarnessTests(unittest.TestCase):
    def test_no_test_class_shadows_testcase_methods(self):
        for m in pkgutil.iter_modules(tests.__path__):
            importlib.import_module(f"tests.{m.name}")
        def subclasses(c):
            for s in c.__subclasses__():
                yield s
                yield from subclasses(s)
        for cls in subclasses(unittest.TestCase):
            if not cls.__module__.startswith("tests."):
                continue
            for name in RESERVED - {"setUp", "tearDown"}:
                with self.subTest(cls=cls.__name__, name=name):
                    self.assertIs(getattr(cls, name), getattr(unittest.TestCase, name),
                                  f"{cls.__name__}.{name} shadows unittest.TestCase.{name}")

    def test_every_wifcase_subclass_has_tests(self):
        for m in pkgutil.iter_modules(tests.__path__):
            importlib.import_module(f"tests.{m.name}")
        for cls in WifCase.__subclasses__():
            with self.subTest(cls=cls.__name__):
                self.assertTrue(any(n.startswith("test") for n in dir(cls)), cls.__name__)
