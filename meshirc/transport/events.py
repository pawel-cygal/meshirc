from dataclasses import dataclass
from datetime import datetime

BROADCAST_NUM = 0xFFFFFFFF


@dataclass(frozen=True)
class TextMessage:
    """Text packet received from the mesh."""

    packet_id: int
    ts: datetime
    from_id: str
    to_id: int
    channel: int
    text: str


@dataclass(frozen=True)
class NodeUpdate:
    """Node info updated (new node seen, name change, telemetry refresh)."""

    node_id: str
    long_name: str
    short_name: str
    last_heard: datetime | None


@dataclass(frozen=True)
class Disconnect:
    """Transport disconnected (radio offline, TCP closed, etc.)."""

    reason: str
