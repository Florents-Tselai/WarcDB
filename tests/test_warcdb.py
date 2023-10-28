import os
import pathlib
import re

import pytest
import sqlite_utils
from click.testing import CliRunner
from warcdb import warcdb_cli

db_file = "test_warc.db"
tests_dir = pathlib.Path(__file__).parent

# all these WARC files were created with wget except for apod.warc.gz which was
# created with browsertrix-crawler


@pytest.mark.parametrize(
    "warc_path",
    [
        str(tests_dir / "google.warc"),
        str(tests_dir / "google.warc.gz"),
        str(tests_dir / "no-warc-info.warc"),
        str(tests_dir / "scoop.wacz"),
        "https://tselai.com/data/google.warc",
        "https://tselai.com/data/google.warc.gz",
    ],
)
def test_import(warc_path):
    runner = CliRunner()
    args = ["import", db_file, warc_path]
    result = runner.invoke(warcdb_cli, args)
    assert result.exit_code == 0
    db = sqlite_utils.Database(db_file)
    assert set(db.table_names()) == {
        "metadata",
        "request",
        "resource",
        "response",
        "warcinfo",
        "_sqlite_migrations",
    }

    if warc_path == str(tests_dir / "google.warc"):
        assert db.table("warcinfo").get(
            "<urn:uuid:7ABED2CA-7CBD-48A0-92E5-0059EBFC111A>"
        )
        assert db.table("request").get(
            "<urn:uuid:524F62DD-D788-4085-B14D-22B0CDC0AC53>"
        )

    os.remove(db_file)


def test_column_names():
    runner = CliRunner()
    runner.invoke(
        warcdb_cli, ["import", db_file, str(pathlib.Path("tests/google.warc"))]
    )

    # make sure that the columns are named correctly (lowercase with underscores)
    db = sqlite_utils.Database(db_file)
    for table in db.tables:
        for col in table.columns:
            assert re.match(r"^[a-z_]+", col.name), f"column {col.name} named correctly"

    os.remove(db_file)


def test_http_header():
    runner = CliRunner()
    runner.invoke(
        warcdb_cli, ["import", db_file, str(pathlib.Path("tests/google.warc"))]
    )

    db = sqlite_utils.Database(db_file)
    headers = list(db["http_header"].rows)
    assert len(headers) == 43
    assert {
        "name": "content-type",
        "value": "text/html; charset=UTF-8",
        "warc_record_id": "<urn:uuid:2008CBED-030B-435B-A4DF-09A842DDB764>",
    } in headers
