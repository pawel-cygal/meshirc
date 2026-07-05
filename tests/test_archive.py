from datetime import datetime

from meshirc.archive import MessageArchive
from meshirc.core.models import Buffer, BufferKind, Message


def test_archive_records_and_reads_recent_messages(tmp_path):
    archive = MessageArchive(tmp_path / "archive.sqlite3")
    archive.open()
    try:
        buf = Buffer(kind=BufferKind.CHANNEL, name="#chan0", target=0)
        archive.record(
            buf,
            Message(ts=datetime(2026, 1, 2, 3, 4), from_id="me", text="hello"),
            direction="out",
        )
        archive.record(
            buf,
            Message(ts=datetime(2026, 1, 2, 3, 5), from_id="!abc", text="hi"),
            direction="in",
        )

        rows = archive.recent("#chan0", limit=10)
        assert [row.text for row in rows] == ["hello", "hi"]
        assert rows[0].direction == "out"
        assert rows[1].from_id == "!abc"
    finally:
        archive.close()


def test_disabled_archive_is_noop(tmp_path):
    archive = MessageArchive(tmp_path / "archive.sqlite3", enabled=False)
    archive.open()
    buf = Buffer(kind=BufferKind.CHANNEL, name="#chan0", target=0)
    archive.record(
        buf,
        Message(ts=datetime(2026, 1, 2, 3, 4), from_id="me", text="hello"),
        direction="out",
    )
    assert archive.recent("#chan0") == []
    assert not (tmp_path / "archive.sqlite3").exists()
