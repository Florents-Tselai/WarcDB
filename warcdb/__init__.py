import datetime
import zipfile
from collections.abc import MutableMapping
from functools import cache
from itertools import chain
from json import dumps

import click
import requests as req
import sqlite_utils
from more_itertools import always_iterable
from tqdm import tqdm
from warcio import ArchiveIterator, StatusAndHeaders
from warcio.recordloader import ArcWarcRecord

from warcdb.migrations import migration


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
    return {k.lower().replace('-', '_'): v for k, v in self.rec_headers.headers}


setattr(ArcWarcRecord, 'as_dict', record_as_dict)

""" Monkeypatch warcio.ArcWarcRecord.to_json() """


# def record_to_json(self):
#     return dumps(self.as_dict())
#
#
# setattr(ArcWarcRecord, 'to_json', record_to_json)


class WarcDB(MutableMapping):
    """
    Wrapper around sqlite_utils.Database

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
        * Todo pass conversions: {'Content-Length': int, warc-date: datet
        * All 'response', 'resource', 'request', 'revisit', 'conversion' and 'continuation' records may have a payload.
        All 'warcinfo' and 'metadata' records shall not have a payload.
        """
        col_type_conversions = {
            'content_length': int,
            'payload': str,
            'warc_date': datetime.datetime,

        }
        record_dict = r.as_dict()

        # Certain rec_types have payload
        has_payload = r.rec_type in ['warcinfo', 'request', 'response', 'metadata', 'resource']
        if has_payload:
            record_dict['payload'] = r.payload()

        # Certain rec_types have http_headers
        has_http_headers = r.http_headers is not None
        if has_http_headers:
            record_dict['http_headers'] = r.http_headers.to_json()

        """Depending on the record type we insert to appropriate record"""
        if r.rec_type == 'warcinfo':

            self.db.table('warcinfo').insert(record_dict,
                                             pk='warc_record_id',
                                             alter=True,
                                             ignore=True,
                                             columns=col_type_conversions)
        elif r.rec_type == 'request':
            self.db.table('request').insert(record_dict,
                                            pk='warc_record_id',
                                            foreign_keys=[
                                                ("warc_warcinfo_id", "warcinfo", "warc-record-id")
                                            ],
                                            alter=True,
                                            ignore=True,
                                            columns=col_type_conversions
                                            )

        elif r.rec_type == 'response':
            self.db.table('response').insert(record_dict,
                                             pk='warc_record_id',
                                             foreign_keys=[
                                                 ("warc_warcinfo_id", "warcinfo", "warc_record_id"),
                                                 ("warc_concurrent_to", "request", "warc_record_id")
                                             ],
                                             alter=True,
                                             ignore=True,
                                             columns=col_type_conversions
                                             )

        elif r.rec_type == 'metadata':
            self.db.table('metadata').insert(record_dict,
                                             pk='warc_record_id',
                                             foreign_keys=[
                                                 ("warc-warcinfo-id", "warcinfo", "warc_record_id"),
                                                 ("warc_concurrent_to", "response", "warc_record_id")
                                             ],
                                             alter=True,
                                             ignore=True,
                                             columns=col_type_conversions
                                             )

        elif r.rec_type == 'resource':
            self.db.table('resource').insert(record_dict,
                                             pk='warc_record_id',
                                             foreign_keys=[
                                                 ("warc-warcinfo-id", "warcinfo", "warc_record_id"),
                                                 ("warc_concurrent_to", "metadata", "warc_record_id")
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


@warcdb_cli.command('init')
@click.argument(
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, exists=False, allow_dash=False),
)
def init (db_path):
    """
    Initialize a new warcdb database
    """
    db = WarcDB(db_path)
    migration.apply(db.db)


@warcdb_cli.command('import')
@click.argument(
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, exists=True, allow_dash=False),
)
@click.argument('warc_path',
                type=click.STRING,
                nargs=-1
                )
@click.option('--batch-size',
              type=click.INT, default=1000,
              help="Batch size for chunked INSERTs [Note: ignored for now]", )
def import_(db_path, warc_path, batch_size):
    """
    Import a WARC file into the database
    """
    db = WarcDB(db_path, batch_size=batch_size)

    # if batch_size:
    #    warnings.warn("--batch-size has been temporarily disabled")

    def to_import():
        for f in always_iterable(warc_path):
            if f.startswith('http'):
                yield from tqdm(ArchiveIterator(req.get(f, stream=True).raw, arc2warc=True), desc=f)
            elif f.endswith('.wacz'):
                # TODO: can we support loading WACZ files by URL?
                wacz = zipfile.ZipFile(f)
                warcs = filter(lambda f: f.filename.endswith('warc.gz'), wacz.infolist())
                for warc in warcs:
                    yield from tqdm(ArchiveIterator(wacz.open(warc.filename, 'r'), arc2warc=True), desc=warc.filename)
            else:
                yield from tqdm(ArchiveIterator(open(f, 'rb'), arc2warc=True), desc=f)

    for r in to_import():
        db += r
