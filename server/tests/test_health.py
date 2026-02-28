import unittest

from fastapi.testclient import TestClient

from app.main import app
from app.sim_agent import MockSimAgent


class TestHealth(unittest.TestCase):

    def setUp(self):
        # Ensure sim_agent is available on app state (lifespan isn't run by TestClient)
        app.state.sim_agent = MockSimAgent(seed=42)
        self.client = TestClient(app)

    def test_health_returns_ok(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})

    def test_mission_status_returns_data(self):
        resp = self.client.get("/mission/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("status", data)
        self.assertIn("mission", data)
        self.assertIn("tick", data)
