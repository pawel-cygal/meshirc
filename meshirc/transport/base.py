from collections.abc import Callable
from typing import Protocol

from meshirc.transport.events import Disconnect, NodeUpdate, TextMessage

EventHandler = Callable[[TextMessage | NodeUpdate | Disconnect], None]


class Transport(Protocol):
    my_node_id: str
    my_node_num: int
    my_short_name: str

    @property
    def target_label(self) -> str: ...

    def start(self, on_event: EventHandler) -> None:
        """Connect and begin emitting events."""

    def reconnect(self, target: str | None = None) -> None:
        """Reconnect to the same target or switch target first."""

    def send_text(
        self, text: str, *, channel: int | None = None, dest_id: str | None = None
    ) -> int:
        """Send a text message and return the packet id."""

    def list_channels(self) -> dict[int, str]:
        """Active channels by index."""

    def list_nodes(self) -> list[NodeUpdate]:
        """Snapshot of currently known nodes."""

    def close(self) -> None: ...
