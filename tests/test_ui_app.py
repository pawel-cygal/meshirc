import asyncio

import pytest

from meshirc.config import ArchiveConfig, Config
from meshirc.transport.events import NodeUpdate
from meshirc.ui.app import MeshircApp


class DummyTransport:
    my_node_id = "!00000001"
    my_node_num = 1
    my_short_name = "ME"
    target_label = "dummy"

    def __init__(self) -> None:
        self.sent: list[tuple[str, int | None, str | None]] = []

    def start(self, on_event) -> None:
        self.on_event = on_event

    def reconnect(self, target: str | None = None) -> None:
        return None

    def send_text(
        self, text: str, *, channel: int | None = None, dest_id: str | None = None
    ) -> int:
        self.sent.append((text, channel, dest_id))
        return 123

    def list_channels(self) -> dict[int, str]:
        return {0: "#primary", 1: "#chat"}

    def list_nodes(self) -> list[NodeUpdate]:
        return [
            NodeUpdate(
                node_id="!00000002",
                long_name="Bob",
                short_name="BOB",
                last_heard=None,
            )
        ]

    def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_app_run_test_exits_cleanly_without_hardware():
    cfg = Config()
    cfg.archive = ArchiveConfig(enabled=False)
    transport = DummyTransport()
    app = MeshircApp(transport, cfg)

    async def run_smoke() -> None:
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause(0.2)
            await pilot.press("alt+2")
            await pilot.press("h", "i", "enter")
            await pilot.pause(0.2)

    await asyncio.wait_for(run_smoke(), timeout=5)

    assert transport.sent == [("hi", 0, None)]
