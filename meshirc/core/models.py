from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


@dataclass
class Node:
    id: str
    long_name: str
    short_name: str
    last_heard: datetime | None = None


@dataclass
class Message:
    ts: datetime
    from_id: str
    text: str
    is_mention: bool = False


class BufferKind(Enum):
    CONSOLE = "console"
    CHANNEL = "channel"
    DM = "dm"


@dataclass
class Buffer:
    kind: BufferKind
    name: str
    target: int | str | None = None
    max_messages: int = 2000
    messages: deque[Message] = field(default_factory=deque)
    unread: int = 0
    has_mention: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.messages, deque) or self.messages.maxlen != self.max_messages:
            self.messages = deque(self.messages, maxlen=self.max_messages)

    def append(self, msg: Message) -> None:
        self.messages.append(msg)
        self.unread += 1
        if msg.is_mention:
            self.has_mention = True

    def mark_read(self) -> None:
        self.unread = 0
        self.has_mention = False
