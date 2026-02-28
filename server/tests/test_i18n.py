import unittest

from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app


class FakeDB:
    def __init__(self):
        self.rows = {}

    def query(self, sql, params=None):
        if sql.startswith("UPSERT") and params:
            rec = params["translations"]
            self.rows[params["key"]] = rec
            return [{"status": "OK"}]

        if sql.startswith("SELECT"):
            return [{"result": list(self.rows.values())}]

        return []

    def create(self, _rid, payload):
        self.rows[payload["key"]] = payload
        return payload

    def select(self, _table):
        return list(self.rows.values())


class TestI18nEndpoint(unittest.TestCase):
    def setUp(self):
        self.fake_db = FakeDB()

        def _override_get_db():
            yield self.fake_db

        app.dependency_overrides[get_db] = _override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_translations_endpoint_returns_catalog(self):
        resp = self.client.get("/i18n/translations?locale=en-US")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["locale"], "en-US")
        self.assertEqual(data["fallback"], "en-US")
        self.assertIn("app.title", data["translations"])
        self.assertEqual(data["translations"]["app.title"], "Mars Mission Control")

    def test_invalid_locale_falls_back_to_en_us(self):
        resp = self.client.get("/i18n/translations?locale=xx-XX")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["locale"], "en-US")

    def test_new_locales_are_exposed(self):
        resp = self.client.get("/i18n/translations?locale=en-US")
        self.assertEqual(resp.status_code, 200)
        codes = {item["code"] for item in resp.json()["locales"]}

        self.assertIn("fr-FR", codes)
        self.assertIn("pt-PT", codes)
        self.assertIn("de-DE", codes)
        self.assertIn("uk-UA", codes)


if __name__ == "__main__":
    unittest.main()
