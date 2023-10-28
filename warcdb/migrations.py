from sqlite_migrate import Migrations

migration = Migrations("warcdb")


@migration()
def m001_initial(db):
    db["warcinfo"].create(
        {
            "warc_type": str,
            "content_type": str,
            "warc_date": str,
            "warc_record_id": str,
            "warc_filename": str,
            "warc_block_digest": str,
            "content_length": int,
            "payload": str,
        },
        pk="warc_record_id",
    )

    db["request"].create(
        {
            "warc_type": str,
            "warc_target_uri": str,
            "content_type": str,
            "warc_date": str,
            "warc_record_id": str,
            "warc_ip_address": str,
            "warc_warcinfo_id": str,
            "warc_block_digest": str,
            "content_length": int,
            "payload": str,
            "http_headers": str,
        },
        pk="warc_record_id",
        foreign_keys=[("warc_warcinfo_id", "warcinfo", "warc_record_id")],
    )

    db["response"].create(
        {
            "warc_type": str,
            "warc_record_id": str,
            "warc_warcinfo_id": str,
            "warc_concurrent_to": str,
            "warc_target_uri": str,
            "warc_date": str,
            "warc_ip_address": str,
            "warc_block_digest": str,
            "warc_payload_digest": str,
            "content_type": str,
            "content_length": int,
            "payload": str,
            "http_headers": str,
        },
        pk="warc_record_id",
        foreign_keys=[
            ("warc_warcinfo_id", "warcinfo", "warc_record_id"),
            ("warc_concurrent_to", "request", "warc_record_id"),
        ],
    )

    db["metadata"].create(
        {
            "warc_type": str,
            "warc_record_id": str,
            "warc_warcinfo_id": str,
            "warc_target_uri": str,
            "warc_date": str,
            "warc_block_digest": str,
            "content_type": str,
            "content_length": int,
            "payload": str,
        },
        pk="warc_record_id",
        foreign_keys=[("warc_warcinfo_id", "warcinfo", "warc_record_id")],
    )

    db["resource"].create(
        {
            "warc_type": str,
            "warc_record_id": str,
            "warc_warcinfo_id": str,
            "warc_concurrent_to": str,
            "warc_target_uri": str,
            "warc_date": str,
            "warc_block_digest": str,
            "content_type": str,
            "content_length": int,
            "payload": str,
        },
        pk="warc_record_id",
        foreign_keys=[
            ("warc_warcinfo_id", "warcinfo", "warc_record_id"),
            ("warc_concurrent_to", "metadata", "warc_record_id"),
        ],
    )


@migration()
def m002_headers(db):
    db.create_view(
        "http_header",
        """
            SELECT
                response.warc_record_id AS warc_record_id,
                LOWER(JSON_EXTRACT(header.VALUE, '$.header')) AS name,
                JSON_EXTRACT(header.VALUE, '$.value') AS value
            FROM response, JSON_EACH(response.http_headers) AS header
        """,
    )
