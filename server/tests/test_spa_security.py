import shutil
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.testclient import TestClient


class TestSpaPathTraversal(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.ui_dir = Path(self.tmpdir)
        self.index = self.ui_dir / "index.html"
        self.index.write_text("<html>index</html>")
        (self.ui_dir / "assets").mkdir()
        (self.ui_dir / "assets" / "app.js").write_text("console.log('ok')")
        secret = Path(self.tmpdir).parent / "secret.txt"
        secret.write_text("SECRET")
        self._secret = secret

        app = FastAPI()
        ui_dir = self.ui_dir
        ui_dir_resolved = ui_dir.resolve()
        index_html = self.index

        @app.get("/{path:path}")
        async def spa_fallback(path: str):
            candidate = (ui_dir / path).resolve()
            if not str(candidate).startswith(str(ui_dir_resolved)):
                return FileResponse(index_html)
            if candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(index_html)

        self.client = TestClient(app)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        if self._secret.exists():
            self._secret.unlink()

    def test_normal_file_served(self):
        resp = self.client.get("/assets/app.js")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("console.log", resp.text)

    def test_unknown_path_returns_index(self):
        resp = self.client.get("/some/spa/route")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("index", resp.text)

    def test_path_traversal_blocked(self):
        resp = self.client.get("/../secret.txt")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("SECRET", resp.text)
        self.assertIn("index", resp.text)

    def test_encoded_traversal_blocked(self):
        resp = self.client.get("/..%2Fsecret.txt")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("SECRET", resp.text)
