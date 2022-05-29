import click
from sqlite_utils import Database
from textwrap import dedent
from warcio.recordbuilder import StatusAndHeaders
from json import JSONEncoder, dumps
from warcio import ArchiveIterator


def always_iterable(obj, base_type=(str, bytes)):
    """If *obj* is iterable, return an iterator over its items::

        >>> obj = (1, 2, 3)
        >>> list(always_iterable(obj))
        [1, 2, 3]

    If *obj* is not iterable, return a one-item iterable containing *obj*::

        >>> obj = 1
        >>> list(always_iterable(obj))
        [1]

    If *obj* is ``None``, return an empty iterable:

        >>> obj = None
        >>> list(always_iterable(None))
        []

    By default, binary and text strings are not considered iterable::

        >>> obj = 'foo'
        >>> list(always_iterable(obj))
        ['foo']

    If *base_type* is set, objects for which ``isinstance(obj, base_type)``
    returns ``True`` won't be considered iterable.

        >>> obj = {'a': 1}
        >>> list(always_iterable(obj))  # Iterate over the dict's keys
        ['a']
        >>> list(always_iterable(obj, base_type=dict))  # Treat dicts as a unit
        [{'a': 1}]

    Set *base_type* to ``None`` to avoid any special handling and treat objects
    Python considers iterable as iterable:

        >>> obj = 'foo'
        >>> list(always_iterable(obj, base_type=None))
        ['f', 'o', 'o']
    """
    if obj is None:
        return iter(())

    if (base_type is not None) and isinstance(obj, base_type):
        return iter((obj,))

    try:
        return iter(obj)
    except TypeError:
        return iter((obj,))


class StatusAndHeadersJsonEncoder(JSONEncoder):
    def default(self, o: StatusAndHeaders):
        if isinstance(o, StatusAndHeaders):
            ret = {
                'protocol': o.protocol,
                'headers': dict(o.headers)
            }
            try:
                ret['status_code'] = o.get_statuscode()
            except IndexError:
                ret['status_code'] = None

            return super().encode(ret)
        else:
            return super().default(o)


class WarcDB(Database):
    """
    Wraper around sqlite_utils.Database

    The schema defined is table storing warcio.ArcWarcRecord objects

    (self.format, self.rec_type, self.rec_headers, self.raw_stream,
         self.http_headers, self.content_type, self.length) = args
        self.payload_length = kwargs.get('payload_length', -1)
    """
    _schema = dedent("""\n
    CREATE TABLE IF NOT EXISTS records (
        format text,
        rec_type text,
        rec_headers json,
        content_stream text,
        http_headers json,
        content_type text,
        length_ int,
        payload_length int default -1
    )""")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conn.execute(self._schema)

    def __iadd__(self, fileobj):
        for f in always_iterable(fileobj):
            with open(f, 'rb') as stream:
                self.table('records').insert_all(
                    ({
                        'format': r.format,
                        'rec_type': r.rec_type,
                        'rec_headers': dumps(r.rec_headers, cls=StatusAndHeadersJsonEncoder),
                        'content_stream': r.content_stream().read(),
                        'http_headers': dumps(r.http_headers, cls=StatusAndHeadersJsonEncoder),
                        'content_type': r.content_type,
                        'length_': r.length,
                        'payload_length': r.payload_length
                    } for r in ArchiveIterator(stream)
                    )
                )


@click.group(name='cli')
def cli():
    """CLI tool to load WARC (and ARC) files into SQLite"""
    pass


@cli.command('import')
@click.argument('files', nargs=-1)
@click.argument('dest')
def import_(files, dest):
    db = WarcDB(dest)
    db += files
