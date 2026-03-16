"""SPA fallback security tests.

Verifies that the allowlist-based static file serving prevents path-traversal
attacks while still serving legitimate assets and SPA routes.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.testclient import TestClient


def _build_spa_app(ui_dir: Path) -> FastAPI:
    """Create a minimal FastAPI app using the same allowlist pattern as prod.

    Static files are indexed at startup; the handler only does a dict lookup,
    so user input never flows into a filesystem path.
    """
    app = FastAPI()
    index_html = ui_dir / "index.html"

    static_files: dict[str, Path] = {}
    for child in ui_dir.rglob("*"):
        if child.is_file() and child.name != "index.html":
            rel = child.relative_to(ui_dir).as_posix()
            static_files[rel] = child

    @app.get("/{path:path}")
    async def spa_fallback(path: str):
        asset = static_files.get(path)
        if asset is not None:
            return FileResponse(asset)
        return FileResponse(index_html)

    return app


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

        self.client = TestClient(_build_spa_app(self.ui_dir))

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
