from click.testing import CliRunner
from warcdb import warcdb_cli
import pathlib
import pytest
import sqlite_utils
from unittest import TestCase

tests_dir = pathlib.Path(__file__).parent


@pytest.mark.parametrize("warc_path", [str(tests_dir / "google.warc"),
                                       str(tests_dir / "google.warc.gz"),
                                       "https://tselai.com/data/google.warc",
                                       "https://tselai.com/data/google.warc.gz"
                                       ])
def test_import(warc_path):
    runner = CliRunner()

    with runner.isolated_filesystem() as fs:
        DB_FILE = "test_warc.db"

        args = ["import", DB_FILE, warc_path]
        result = runner.invoke(warcdb_cli, args)
        assert result.exit_code == 0
        db = sqlite_utils.Database(DB_FILE)
        assert set(db.table_names()) == {
            'metadata', 'request', 'resource', 'response', 'warcinfo'
        }

        if warc_path == str(tests_dir / "google.warc"):
            assert db.table('warcinfo').get('<urn:uuid:7ABED2CA-7CBD-48A0-92E5-0059EBFC111A>')
            assert db.table('request').get('<urn:uuid:524F62DD-D788-4085-B14D-22B0CDC0AC53>')
