"""Tests for configuration used by the Label Resolution analysis data loader."""
import os
import unittest
from unittest.mock import patch

import config


class TestLabelResolutionConfig(unittest.TestCase):
    def setUp(self):
        self.original_config = config._config
        config._config = {"ENPM611_PROJECT_DATA_PATH": "/tmp/label-resolution-issues.json"}
        self.original_env = os.environ.pop("ENPM611_PROJECT_DATA_PATH", None)

    def tearDown(self):
        os.environ.pop("ENPM611_PROJECT_DATA_PATH", None)
        if self.original_env is not None:
            os.environ["ENPM611_PROJECT_DATA_PATH"] = self.original_env
        config._config = self.original_config

    def test_label_resolution_dataset_path_is_read_from_config(self):
        self.assertEqual(
            config.get_parameter("ENPM611_PROJECT_DATA_PATH"),
            "/tmp/label-resolution-issues.json",
        )

    def test_environment_dataset_path_overrides_config(self):
        os.environ["ENPM611_PROJECT_DATA_PATH"] = "/tmp/override-issues.json"
        self.assertEqual(
            config.get_parameter("ENPM611_PROJECT_DATA_PATH"),
            "/tmp/override-issues.json",
        )

    def test_missing_dataset_path_returns_none(self):
        config._config = {}
        self.assertIsNone(config.get_parameter("ENPM611_PROJECT_DATA_PATH"))

    def test_json_prefixed_environment_path_is_converted(self):
        os.environ["ENPM611_PROJECT_DATA_PATH"] = 'json:"/tmp/issues.json"'
        self.assertEqual(
            config.get_parameter("ENPM611_PROJECT_DATA_PATH"),
            "/tmp/issues.json",
        )


if __name__ == "__main__":
    unittest.main()
