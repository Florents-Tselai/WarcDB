from sqlite_migrate import Migrations

migration = Migrations("warcdb")


@migration()
def m001_initial(db):
    db["warcinfo"].create(
        {
            "WARC-Type": str,
            "Content-Type": str,
            "WARC-Date": str,
            "WARC-Record-ID": str,
            "WARC-Filename": str,
            "WARC-Block-Digest": str,
            "Content-Length": int,
            "payload": str,
        },
        pk="WARC-Record-ID",
    )

    db["request"].create(
        {
            "WARC-Type": str,
            "WARC-Target-URI": str,
            "Content-Type": str,
            "WARC-Date": str,
            "WARC-Record-ID": str,
            "WARC-IP-Address": str,
            "WARC-Warcinfo-ID": str,
            "WARC-Block-Digest": str,
            "Content-Length": int,
            "payload": str,
            "http_headers": str,
        },
        pk="WARC-Record-ID",
        foreign_keys=[("WARC-Warcinfo-ID", "warcinfo", "WARC-Record-ID")],
    )

    db["response"].create(
        {
            "WARC-Type": str,
            "WARC-Record-ID": str,
            "WARC-Warcinfo-ID": str,
            "WARC-Concurrent-To": str,
            "WARC-Target-URI": str,
            "WARC-Date": str,
            "WARC-IP-Address": str,
            "WARC-Block-Digest": str,
            "WARC-Payload-Digest": str,
            "Content-Type": str,
            "Content-Length": int,
            "payload": str,
            "http_headers": str,
        },
        pk="WARC-Record-ID",
        foreign_keys=[
            ("WARC-Warcinfo-ID", "warcinfo", "WARC-Record-ID"),
            ("WARC-Concurrent-To", "request", "WARC-Record-ID"),
        ],
    )

    db["metadata"].create(
        {
            "WARC-Type": str,
            "WARC-Record-ID": str,
            "WARC-Warcinfo-ID": str,
            "WARC-Target-URI": str,
            "WARC-Date": str,
            "WARC-Block-Digest": str,
            "Content-Type": str,
            "Content-Length": int,
            "payload": str,
        },
        pk="WARC-Record-ID",
        foreign_keys=[("WARC-Warcinfo-ID", "warcinfo", "WARC-Record-ID")],
    )

    db["resource"].create(
        {
            "WARC-Type": str,
            "WARC-Record-ID": str,
            "WARC-Warcinfo-ID": str,
            "WARC-Concurrent-To": str,
            "WARC-Target-URI": str,
            "WARC-Date": str,
            "WARC-Block-Digest": str,
            "Content-Type": str,
            "Content-Length": int,
            "payload": str,
        },
        pk="WARC-Record-ID",
        foreign_keys=[
            ("WARC-Warcinfo-ID", "warcinfo", "WARC-Record-ID"),
            ("WARC-Concurrent-To", "metadata", "WARC-Record-ID"),
        ],
    )
