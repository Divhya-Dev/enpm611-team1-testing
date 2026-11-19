"""Unit tests for run.py (command-line entry point).

run.py parses arguments and dispatches at import time, so each test executes
it with runpy under a patched ``sys.argv`` and with the analyses replaced by
mocks. This verifies argument parsing and dispatch without running analyses.
"""
import contextlib
import io
import os
import runpy
import sys
import unittest
from pathlib import Path
from unittest import mock

import config

RUN_PY = str(Path(__file__).resolve().parent.parent / "run.py")


class TestRunEntryPoint(unittest.TestCase):

    def setUp(self):
        saved = config._config
        config._config = {}
        self.addCleanup(setattr, config, "_config", saved)

        env = mock.patch.dict(os.environ, {}, clear=False)
        env.start()
        self.addCleanup(env.stop)

        self.issues = ["issue-a", "issue-b"]
        loader = mock.patch("data_loader.DataLoader")
        self.loader_cls = loader.start()
        self.loader_cls.return_value.get_issues.return_value = self.issues
        self.addCleanup(loader.stop)

        self.label_run = self._patch("label_resolution_analysis.run")
        self.contributor_run = self._patch("contributor_activity_analysis.run")
        self.discussion_run = self._patch("discussion_trend_analysis.run")
        self.example_cls = self._patch("example_analysis.ExampleAnalysis")

    def _patch(self, target):
        patcher = mock.patch(target)
        mocked = patcher.start()
        self.addCleanup(patcher.stop)
        return mocked

    def _invoke(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "argv", ["run.py", *argv]), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            namespace = runpy.run_path(RUN_PY, run_name="__main__")
        return namespace, out.getvalue(), err.getvalue()

    def test_feature_1_runs_label_resolution_with_label(self):
        self._invoke("--feature", "1", "--label", "kind/bug")
        self.label_run.assert_called_once_with(self.issues, label="kind/bug")
        self.contributor_run.assert_not_called()
        self.discussion_run.assert_not_called()

    def test_feature_1_without_label_passes_none(self):
        self._invoke("--feature", "1")
        self.label_run.assert_called_once_with(self.issues, label=None)

    def test_feature_2_runs_contributor_activity(self):
        self._invoke("--feature", "2")
        self.contributor_run.assert_called_once_with(self.issues)
        self.label_run.assert_not_called()
        self.discussion_run.assert_not_called()

    def test_feature_3_runs_discussion_trend_with_label(self):
        self._invoke("--feature", "3", "--label", "kind/feature")
        self.discussion_run.assert_called_once_with(self.issues, label="kind/feature")
        self.label_run.assert_not_called()
        self.contributor_run.assert_not_called()

    def test_feature_0_runs_example_analysis(self):
        self._invoke("--feature", "0")
        self.example_cls.assert_called_once_with()
        self.example_cls.return_value.run.assert_called_once_with()
        self.loader_cls.assert_not_called()

    def test_unknown_feature_prints_help_message(self):
        _, out, _ = self._invoke("--feature", "9")
        self.assertIn("Need to specify which feature to run with --feature flag.", out)
        for runner in (self.label_run, self.contributor_run, self.discussion_run):
            runner.assert_not_called()

    def test_short_flags_are_accepted(self):
        namespace, _, _ = self._invoke("-f", "1", "-l", "area/docs", "-u", "ada")
        args = namespace["args"]
        self.assertEqual((args.feature, args.label, args.user), (1, "area/docs", "ada"))

    def test_arguments_are_published_to_config(self):
        self._invoke("--feature", "1", "--label", "kind/bug", "--user", "ada")
        self.assertEqual(config.get_parameter("label"), "kind/bug")
        self.assertEqual(config.get_parameter("user"), "ada")
        self.assertEqual(config.get_parameter("feature"), 1)

    def test_missing_feature_flag_exits_with_usage_error(self):
        with self.assertRaises(SystemExit) as ctx:
            self._invoke()
        self.assertEqual(ctx.exception.code, 2)

    def test_non_integer_feature_exits_with_usage_error(self):
        with self.assertRaises(SystemExit) as ctx:
            self._invoke("--feature", "one")
        self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
