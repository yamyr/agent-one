"""Tests for Settings configuration defaults and validation."""

import unittest

from pydantic import ValidationError

from app.config import Settings


class TestDroneTurnIntervalSetting(unittest.TestCase):
    """Ensure drone_turn_interval_seconds is configurable with correct defaults."""

    def test_default_value(self):
        s = Settings(mistral_api_key="test")
        self.assertEqual(s.drone_turn_interval_seconds, 3.5)

    def test_custom_value(self):
        s = Settings(mistral_api_key="test", drone_turn_interval_seconds=10.0)
        self.assertEqual(s.drone_turn_interval_seconds, 10.0)

    def test_rejects_zero(self):
        with self.assertRaises(ValidationError):
            Settings(mistral_api_key="test", drone_turn_interval_seconds=0)

    def test_rejects_negative(self):
        with self.assertRaises(ValidationError):
            Settings(mistral_api_key="test", drone_turn_interval_seconds=-1.0)


class TestEventWindowTicksSetting(unittest.TestCase):
    """Ensure event_window_ticks is configurable with correct defaults."""

    def test_default_value(self):
        s = Settings(mistral_api_key="test")
        self.assertEqual(s.event_window_ticks, 50)

    def test_custom_value(self):
        s = Settings(mistral_api_key="test", event_window_ticks=100)
        self.assertEqual(s.event_window_ticks, 100)

    def test_rejects_zero(self):
        with self.assertRaises(ValidationError):
            Settings(mistral_api_key="test", event_window_ticks=0)

    def test_rejects_negative(self):
        with self.assertRaises(ValidationError):
            Settings(mistral_api_key="test", event_window_ticks=-1)


if __name__ == "__main__":
    unittest.main()
