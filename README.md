# WarcDB: Web crawl data as SQLite databases.


`WarcDB` is a an `SQLite`-based file format that makes web crawl data easier to share and query.

## Motivation

From the `WARC` [formal specification](https://iipc.github.io/warc-specifications/specifications/warc-format/warc-1.1/):

> The WARC (Web ARChive) file format offers a convention for concatenating multiple resource records (data objects), each consisting of a set of simple text headers and an arbitrary data block into one long file.

Many organizations such as Commoncrawl, WebRecorder, Archive.org and libraries around the world, use the `warc` format to archive and store the web.

From my experience, Commoncrawl in particular offers

## Examples

### Multiple `.warc[gz]` files into a `.warcdb`

```shell
warcdb import ./example.warcdb ./tests/example.warc ./tests/example.warc.gz --batch-size 10000
```

### Pipe `wget -x` to `.warcdb`

TODO 

### Concat multiple `.warcdb`

TODO: use  `ATTACH`


Resources on WARC
----------------
* [The stack: An introduction to the WARC file](https://archive-it.org/blog/post/the-stack-warc-file/)

