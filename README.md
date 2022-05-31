# warcio-SQLite

CLI tool to load WARC (and ARC) files into SQLite

Example
-------

    warcio-sqlite import ./data/example.warc ./data/example.warc.gz warc.db 

```shell
Usage: warcio-sqlite import [OPTIONS] [FILES]... DEST

Options:
  --help  Show this message and exit.
```

```shell
Usage: warcio-sqlite [OPTIONS] COMMAND [ARGS]...

  CLI tool to load WARC (and ARC) files into SQLite

Options:
  --help  Show this message and exit.

Commands:
  import
```