import unittest
from unittest.mock import patch


class TestGetMistralClient(unittest.TestCase):
    @patch("app.llm.Mistral")
    @patch("app.llm.settings")
    def test_creates_client_with_configured_api_key(self, mock_settings, mock_mistral):
        mock_settings.mistral_api_key = "test-key"

        from app.llm import get_mistral_client

        client = get_mistral_client()

        mock_mistral.assert_called_once_with(api_key="test-key")
        self.assertIs(client, mock_mistral.return_value)

    @patch("app.llm.settings")
    def test_raises_when_api_key_missing(self, mock_settings):
        mock_settings.mistral_api_key = ""

        from app.llm import get_mistral_client

        with self.assertRaises(RuntimeError) as ctx:
            get_mistral_client()

        self.assertIn("MISTRAL_API_KEY not set", str(ctx.exception))
