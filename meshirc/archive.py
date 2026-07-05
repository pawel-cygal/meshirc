import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from meshirc.core.models import Buffer, Message


@dataclass(frozen=True)
class ArchivedMessage:
    ts: datetime
    buffer_name: str
    buffer_kind: str
    target: str
    direction: str
    from_id: str
    text: str
    is_mention: bool


class MessageArchive:
    def __init__(self, path: Path | None, *, enabled: bool = True) -> None:
        self.path = path
        self.enabled = enabled
        self._conn: sqlite3.Connection | None = None

    def open(self) -> None:
        if not self.enabled or self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.execute(
            """
            create table if not exists messages (
                id integer primary key autoincrement,
                ts text not null,
                buffer_name text not null,
                buffer_kind text not null,
                target text not null,
                direction text not null,
                from_id text not null,
                text text not null,
                is_mention integer not null default 0
            )
            """
        )
        self._conn.execute(
            "create index if not exists idx_messages_buffer_ts on messages(buffer_name, ts)"
        )
        self._conn.commit()

    def record(self, buffer: Buffer, message: Message, *, direction: str) -> None:
        if self._conn is None:
            return
        self._conn.execute(
            """
            insert into messages(
                ts, buffer_name, buffer_kind, target, direction, from_id, text, is_mention
            ) values (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message.ts.isoformat(timespec="seconds"),
                buffer.name,
                buffer.kind.value,
                "" if buffer.target is None else str(buffer.target),
                direction,
                message.from_id,
                message.text,
                1 if message.is_mention else 0,
            ),
        )
        self._conn.commit()

    def recent(self, buffer_name: str, *, limit: int = 20) -> list[ArchivedMessage]:
        if self._conn is None:
            return []
        rows = self._conn.execute(
            """
            select ts, buffer_name, buffer_kind, target, direction, from_id, text, is_mention
            from messages
            where buffer_name = ?
            order by id desc
            limit ?
            """,
            (buffer_name, limit),
        ).fetchall()
        return [
            ArchivedMessage(
                ts=datetime.fromisoformat(row[0]),
                buffer_name=row[1],
                buffer_kind=row[2],
                target=row[3],
                direction=row[4],
                from_id=row[5],
                text=row[6],
                is_mention=bool(row[7]),
            )
            for row in reversed(rows)
        ]

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
