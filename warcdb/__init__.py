import sys

import click
import sqlite_utils
from textwrap import dedent
import warcio
from json import JSONEncoder, dumps
from warcio import ArchiveIterator, StatusAndHeaders
from more_itertools import always_iterable
from http.client import HTTPMessage, HTTPResponse
from email.parser import Parser, HeaderParser
from collections.abc import MutableMapping
from warcio.recordloader import ArcWarcRecord, ArcWarcRecordLoader
from warcio.recordbuilder import RecordBuilder
from typing import Iterable

from itertools import chain


def dict_union(*args):
    """ Utility function to union multiple dicts """
    # https://stackoverflow.com/a/15936211/1333954
    return dict(chain.from_iterable(d.iteritems() for d in args))


""" Monkeypatch warcio.ArcWarcRecord class """


def record_as_dict(self: ArcWarcRecord):
    ret = dict()

    # Add warc fields as items
    ret.update(dict(self.rec_headers.headers))

    if self.http_headers:
        ret['http_headers'] = dumps(self.http_headers.headers)
    else:
        ret['http_headers'] = None

    ret['payload'] = self.raw_stream.read()

    return ret


setattr(ArcWarcRecord, 'as_dict', record_as_dict)


def record_to_json(self):
    return dumps(self.as_dict())


setattr(ArcWarcRecord, 'to_json', record_to_json)


class WarcDB(MutableMapping):
    """
    Wraper around sqlite_utils.Database

    The schema defined is table storing warcio.ArcWarcRecord objects

    (self.format, self.rec_type, self.rec_headers, self.raw_stream,
         self.http_headers, self.content_type, self.length) = args
        self.payload_length = kwargs.get('payload_length', -1)
    """

    def __init__(self, *args, **kwargs):
        # First pop warcdb - specific params
        self._batch_size = kwargs.pop('batch_size', 1000)
        self._records_table = kwargs.get('records_table', 'records')

        # Pass the rest to sqlite_utils
        self._db = sqlite_utils.Database(*args, **kwargs)

    @property
    def db(self) -> sqlite_utils.Database:
        return self._db

    def table(self, table_name, **kwargs):
        """Convenience method to fetch table by name"""
        return self.db.table(table_name, **kwargs)

    @property
    def records(self):
        """Returns the db table the records are stored"""
        return self.table(self._records_table)

    """MutableMapping abstract methods
    
    WarcDB acts as a Mapping (id: str -> r: ArcWarcRecord).
    
    """

    def __setitem__(self, key, value: ArcWarcRecord):
        """ This is the only client-facing way to mutate the file.
        Any normalization should happen here.
        """
        # Any normalizations happens here
        raise NotImplemented

    def __getitem__(self, item) -> ArcWarcRecord:
        # Any denormalization happens here
        raise NotImplemented

    def __delitem__(self, key):
        raise NotImplemented

    def __iter__(self):
        raise NotImplemented

    def __len__(self):
        return self.records.count

    """ API Methods """

    def __iadd__(self, recs_to_add: Iterable[ArcWarcRecord]):
        self.records.insert_all(
            (r.as_dict() for r in recs_to_add),
            pk='WARC-Record-ID',
            batch_size=self._batch_size,
            alter=True,
            ignore=True
        )


@click.group(name='cli')
def cli():
    """CLI tool to create and manipulate .warcdb files"""
    pass


@cli.command('import')
@click.argument(
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
)
@click.argument('warc_path',
                type=click.Path(file_okay=True, dir_okay=False, allow_dash=False, exists=True),
                nargs=-1
                )
@click.option('--batch-size',
              type=click.INT, default=1000,
              help="Batch size for chunked INSERTs", )
def import_(db_path, warc_path, batch_size):
    db = WarcDB(db_path, batch_size=batch_size)

    def to_import():
        for f in always_iterable(warc_path):
            with open(f, 'rb') as stream:
                for record in ArchiveIterator(stream):
                    yield record

    db += to_import()


def add():
    pass
