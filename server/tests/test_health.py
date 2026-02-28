import unittest

from fastapi.testclient import TestClient

from app.main import app


class TestHealth(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_health_returns_ok(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})

    def test_mission_status_returns_idle(self):
        resp = self.client.get("/mission/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "idle")
