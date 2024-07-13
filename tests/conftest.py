import pytest
import sqlite3


@pytest.fixture
def db_path(tmpdir):
    path = str(tmpdir / "test.db")
    return path
