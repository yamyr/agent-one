import unittest
import subprocess
import time
import os
import socket

from app.config import settings
from app.db import _create_connection

_surreal_process = None
_surreal_log_file = None
_test_port = 8009


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return False
        except socket.error:
            return True


async def rut_session_setup():
    """Start in-memory SurrealDB for testing."""
    global _surreal_process, _surreal_log_file

    log_file_path = os.path.join(os.getcwd(), 'test_surrealdb.log')
    _surreal_log_file = open(log_file_path, 'w')

    _surreal_process = subprocess.Popen([
        'surreal', 'start',
        '--log', 'error',
        '--user', 'root',
        '--pass', 'root',
        '--bind', f'127.0.0.1:{_test_port}',
        'memory'
    ], stdout=_surreal_log_file, stderr=_surreal_log_file)

    for _ in range(30):  # 30 attempts × 0.2s = 6s max
        if is_port_in_use(_test_port):
            break
        time.sleep(0.2)
    else:
        raise RuntimeError(f"SurrealDB failed to start on port {_test_port}")
    print(f"Started in-memory SurrealDB on port {_test_port}")


async def rut_session_teardown():
    """Stop in-memory SurrealDB."""
    global _surreal_process, _surreal_log_file

    if _surreal_process:
        _surreal_process.terminate()
        _surreal_process.wait(timeout=5)
        _surreal_process = None

    if _surreal_log_file:
        _surreal_log_file.close()
        _surreal_log_file = None


class CaseWithDB(unittest.IsolatedAsyncioTestCase):
    """Base test case with real SurrealDB, calling handlers directly."""

    def safe_id(self) -> str:
        return self.id().replace('.', '_')

    def setUp(self):
        settings.surreal_url = f'ws://localhost:{_test_port}/rpc'
        settings.surreal_ns = 'test'
        settings.surreal_db = self.safe_id()
        self.db = _create_connection()

    def tearDown(self):
        if self.db:
            self.db.close()
