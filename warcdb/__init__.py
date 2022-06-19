import datetime
import sys
import warnings
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
from functools import cache
from itertools import chain
import requests as req
from tqdm import tqdm


def dict_union(*args):
    """ Utility function to union multiple dicts """
    # https://stackoverflow.com/a/15936211/1333954
    return dict(chain.from_iterable(d.iteritems() for d in args))


""" Monkeypatch warcio.StatusAndHeaders.to_json() """


def headers_to_json(self):
    return dumps([{'header': h, 'value': v} for h, v in self.headers])


setattr(StatusAndHeaders, 'to_json', headers_to_json)

""" Monkeypatch warcio.ArcWarcRecord.payload """


@cache  # It's important that we cache this, as the content_stream() can only be consumed once.
def record_payload(self: ArcWarcRecord):
    return self.content_stream().read()


setattr(ArcWarcRecord, 'payload', record_payload)

""" Monkeypatch warcio.ArcWarcRecord.as_dict() """


@cache
def record_as_dict(self: ArcWarcRecord):
    """Method to easily represent a record as a dict, to be fed into db_utils.Database.insert()"""

    return dict(self.rec_headers.headers)


setattr(ArcWarcRecord, 'as_dict', record_as_dict)

""" Monkeypatch warcio.ArcWarcRecord.to_json() """


# def record_to_json(self):
#     return dumps(self.as_dict())
#
#
# setattr(ArcWarcRecord, 'to_json', record_to_json)


class WarcDB(MutableMapping):
    """
    Wraper around sqlite_utils.Database

    WarcDB acts as a Mapping (id: str -> r: ArcWarcRecord).


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

    @property
    def http_headers(self):
        return self.table('http_headers')

    @property
    def payloads(self):
        return self.table('payloads')

    """MutableMapping abstract methods"""

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

    def __iadd__(self, r: ArcWarcRecord):
        """
        TODO
        ====

        * For all rec_types: also store WARC/1.0 field (warc and version?)
        * Todo pass conversions: {'Content-Length': int, WARC-Date: datet
        * All 'response', 'resource', 'request', 'revisit', 'conversion' and 'continuation' records may have a payload.
        All 'warcinfo' and 'metadata' records shall not have a payload.
        """
        col_type_conversions = {
            'Content-Length': int,
            'payload': str,
            'WARC-Date': datetime.datetime,

        }
        record_dict = r.as_dict()

        # Certain rec_types have payload
        has_payload = r.rec_type in ['warcinfo', 'request', 'response', 'metadata', 'resource']
        if has_payload:
            record_dict['payload'] = r.payload()

        # Certain rec_types have http_headers
        has_http_headers = r.rec_type in ['request', 'response']
        if has_http_headers:
            record_dict['http_headers'] = r.http_headers.to_json()

        """Depending on the record type we insert to appropriate record"""
        if r.rec_type == 'warcinfo':

            self.db.table('warcinfo').insert(record_dict,
                                             pk='WARC-Record-ID',
                                             alter=True,
                                             ignore=True,
                                             columns=col_type_conversions)
        elif r.rec_type == 'request':
            self.db.table('request').insert(record_dict,
                                            pk='WARC-Record-ID',
                                            foreign_keys=[
                                                ("WARC-Warcinfo-ID", "warcinfo", "WARC-Record-ID")
                                            ],
                                            alter=True,
                                            ignore=True,
                                            columns=col_type_conversions
                                            )

        elif r.rec_type == 'response':
            self.db.table('response').insert(record_dict,
                                             pk='WARC-Record-ID',
                                             foreign_keys=[
                                                 ("WARC-Warcinfo-ID", "warcinfo", "WARC-Record-ID"),
                                                 ("WARC-Concurrent-To", "request", "WARC-Record-ID")
                                             ],
                                             alter=True,
                                             ignore=True,
                                             columns=col_type_conversions
                                             )

        elif r.rec_type == 'metadata':
            self.db.table('metadata').insert(record_dict,
                                             pk='WARC-Record-ID',
                                             foreign_keys=[
                                                 ("WARC-Warcinfo-ID", "warcinfo", "WARC-Record-ID"),
                                                 ("WARC-Concurrent-To", "response", "WARC-Record-ID")
                                             ],
                                             alter=True,
                                             ignore=True,
                                             columns=col_type_conversions
                                             )

        elif r.rec_type == 'resource':
            self.db.table('resource').insert(record_dict,
                                             pk='WARC-Record-ID',
                                             foreign_keys=[
                                                 ("WARC-Warcinfo-ID", "warcinfo", "WARC-Record-ID"),
                                                 ("WARC-Concurrent-To", "metadata", "WARC-Record-ID")
                                             ],
                                             alter=True,
                                             ignore=True,
                                             columns=col_type_conversions
                                             )

        else:
            raise ValueError(f"Record type <{r.rec_type}> is not supported"
                             f"Only [warcinfo, request, response, metadata, resource] are.")
        return self


from sqlite_utils import cli as sqlite_utils_cli

warcdb_cli = sqlite_utils_cli.cli
warcdb_cli.help = \
    "Commands for interacting with .warcdb files\n\nBased on SQLite-Utils"


@warcdb_cli.command('import')
@click.argument(
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
)
@click.argument('warc_path',
                type=click.STRING,
                nargs=-1
                )
@click.option('--batch-size',
              type=click.INT, default=1000,
              help="Batch size for chunked INSERTs [Note: ignored for now]", )
def import_(db_path, warc_path, batch_size):
    db = WarcDB(db_path, batch_size=batch_size)

    # if batch_size:
    #    warnings.warn("--batch-size has been temporarily disabled")

    def to_import():
        for f in always_iterable(warc_path):
            if f.startswith('http'):
                for record in tqdm(ArchiveIterator(req.get(f, stream=True).raw, arc2warc=True),
                                   desc=f):
                    yield record
            else:
                with open(f, 'rb') as stream:
                    for record in tqdm(ArchiveIterator(stream), desc=f):
                        yield record

    for r in to_import():
        db += r
