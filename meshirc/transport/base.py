from collections.abc import Callable
from typing import Protocol

from meshirc.transport.events import Disconnect, NodeUpdate, TextMessage

EventHandler = Callable[[TextMessage | NodeUpdate | Disconnect], None]


class Transport(Protocol):
    """Generic transport interface so the app doesn't depend on TCPInterface directly."""

    my_node_id: str
    my_node_num: int
    my_short_name: str

    def start(self, on_event: EventHandler) -> None:
        """Connect and begin emitting events. Blocks until connected (or raises)."""

    def send_text(
        self, text: str, *, channel: int | None = None, dest_id: str | None = None
    ) -> int:
        """Send a text message. Returns packet_id assigned by the radio."""

    def list_channels(self) -> dict[int, str]:
        """Active channels: {index: name}. Index 0 always present."""

    def list_nodes(self) -> list[NodeUpdate]:
        """Snapshot of currently known nodes."""

    def close(self) -> None: ...
