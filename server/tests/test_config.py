"""Tests for Settings configuration defaults and validation."""

import unittest

from pydantic import ValidationError

from app.config import Settings


class TestDroneTurnIntervalSetting(unittest.TestCase):
    """Ensure drone_turn_interval_seconds is configurable with correct defaults."""

    def test_default_value(self):
        s = Settings(mistral_api_key="test")
        self.assertEqual(s.drone_turn_interval_seconds, 5.0)

    def test_custom_value(self):
        s = Settings(mistral_api_key="test", drone_turn_interval_seconds=10.0)
        self.assertEqual(s.drone_turn_interval_seconds, 10.0)

    def test_rejects_zero(self):
        with self.assertRaises(ValidationError):
            Settings(mistral_api_key="test", drone_turn_interval_seconds=0)

    def test_rejects_negative(self):
        with self.assertRaises(ValidationError):
            Settings(mistral_api_key="test", drone_turn_interval_seconds=-1.0)


if __name__ == "__main__":
    unittest.main()
