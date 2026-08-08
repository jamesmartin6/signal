"""Test DB setup notes:

The app's background pipeline runs (FastAPI BackgroundTasks) open their own
DB session via the module-global SessionLocal/engine — a different
connection than any per-test session we might set up separately. An
in-memory SQLite DB (`:memory:`) is per-connection, so if the background
task's session used a different connection than the test's, it would see an
empty, table-less database (this actually happened during Phase 3
development: `OperationalError: no such table: leads` from inside a
TestClient request, because the background task's thread got its own empty
`:memory:` DB). Using a shared temp *file* instead means every session,
regardless of thread, reads and writes the same real database — exactly
like the SQLite/Postgres file-or-server case in production.
"""

import atexit
import os
import shutil
import tempfile
from pathlib import Path

_tmp_dir = tempfile.mkdtemp(prefix="signal-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_tmp_dir) / 'test.db'}"
atexit.register(shutil.rmtree, _tmp_dir, True)

import pytest
from fastapi.testclient import TestClient

from app.db.models import Base
from app.db.session import SessionLocal, engine
from app.main import app


@pytest.fixture()
def _fresh_schema():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@pytest.fixture()
def db_session(_fresh_schema):
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(_fresh_schema):
    with TestClient(app) as test_client:
        yield test_client
