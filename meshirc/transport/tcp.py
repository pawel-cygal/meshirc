from datetime import datetime
from typing import Any

import meshtastic.tcp_interface
from pubsub import pub

from meshirc.transport.base import EventHandler
from meshirc.transport.events import BROADCAST_NUM, Disconnect, NodeUpdate, TextMessage


def _node_num_to_id(num: int) -> str:
    return f"!{num:08x}"


class MeshtasticTcpTransport:
    """Wraps meshtastic.TCPInterface and bridges pubsub callbacks to typed events.

    pubsub callbacks fire in meshtastic's worker thread — the EventHandler must
    be thread-safe (the app posts to an asyncio.Queue via call_soon_threadsafe).
    """

    def __init__(self, host: str, port: int = 4403) -> None:
        self.host = host
        self.port = port
        self.my_node_id: str = ""
        self.my_node_num: int = 0
        self.my_short_name: str = ""
        self._iface: meshtastic.tcp_interface.TCPInterface | None = None
        self._on_event: EventHandler | None = None

    def start(self, on_event: EventHandler) -> None:
        self._on_event = on_event
        self._iface = meshtastic.tcp_interface.TCPInterface(
            hostname=self.host, portNumber=self.port
        )
        info = self._iface.getMyNodeInfo() or {}
        self.my_node_num = int(info.get("num", 0))
        self.my_node_id = _node_num_to_id(self.my_node_num) if self.my_node_num else "?"
        user = info.get("user", {}) or {}
        self.my_short_name = user.get("shortName") or "?"

        pub.subscribe(self._on_text_packet, "meshtastic.receive.text")
        pub.subscribe(self._on_node_update, "meshtastic.node.updated")
        pub.subscribe(self._on_connection_lost, "meshtastic.connection.lost")

    def _on_text_packet(self, packet: dict[str, Any], interface: Any) -> None:  # noqa: ARG002
        if self._on_event is None:
            return
        decoded = packet.get("decoded", {})
        text = decoded.get("text")
        if not text:
            return
        evt = TextMessage(
            packet_id=int(packet.get("id", 0)),
            ts=datetime.now(),
            from_id=str(packet.get("fromId", "?")),
            to_id=int(packet.get("to", BROADCAST_NUM)),
            channel=int(packet.get("channel", 0)),
            text=text,
        )
        self._on_event(evt)

    def _on_node_update(self, node: dict[str, Any], interface: Any) -> None:  # noqa: ARG002
        if self._on_event is None:
            return
        num = int(node.get("num", 0))
        user = node.get("user") or {}
        last_heard = node.get("lastHeard")
        evt = NodeUpdate(
            node_id=_node_num_to_id(num),
            long_name=user.get("longName") or _node_num_to_id(num),
            short_name=user.get("shortName") or "?",
            last_heard=datetime.fromtimestamp(last_heard) if last_heard else None,
        )
        self._on_event(evt)

    def _on_connection_lost(self, interface: Any) -> None:  # noqa: ARG002
        if self._on_event is not None:
            self._on_event(Disconnect(reason="connection lost"))

    def send_text(
        self, text: str, *, channel: int | None = None, dest_id: str | None = None
    ) -> int:
        assert self._iface is not None, "transport not started"
        kwargs: dict[str, Any] = {}
        if channel is not None:
            kwargs["channelIndex"] = channel
        if dest_id is not None:
            kwargs["destinationId"] = dest_id
        packet = self._iface.sendText(text, **kwargs)
        return int(getattr(packet, "id", 0))

    def list_channels(self) -> dict[int, str]:
        assert self._iface is not None, "transport not started"
        out: dict[int, str] = {}
        node = getattr(self._iface, "localNode", None)
        channels = getattr(node, "channels", None) or []
        for idx, ch in enumerate(channels):
            role_obj = getattr(ch, "role", None)
            role_name = getattr(role_obj, "name", None) if role_obj is not None else None
            if role_name == "DISABLED":
                continue
            settings = getattr(ch, "settings", None)
            name = getattr(settings, "name", "") if settings is not None else ""
            ch_idx = int(getattr(ch, "index", idx))
            out[ch_idx] = f"#{name}" if name else f"#chan{ch_idx}"
        if 0 not in out:
            out[0] = "#chan0"
        return out

    def list_nodes(self) -> list[NodeUpdate]:
        assert self._iface is not None, "transport not started"
        nodes = getattr(self._iface, "nodes", None) or {}
        out: list[NodeUpdate] = []
        for node_id, node in nodes.items():
            user = node.get("user") or {}
            last_heard = node.get("lastHeard")
            out.append(
                NodeUpdate(
                    node_id=str(node_id),
                    long_name=user.get("longName") or str(node_id),
                    short_name=user.get("shortName") or "?",
                    last_heard=datetime.fromtimestamp(last_heard) if last_heard else None,
                )
            )
        return out

    def close(self) -> None:
        if self._iface is not None:
            try:
                pub.unsubscribe(self._on_text_packet, "meshtastic.receive.text")
                pub.unsubscribe(self._on_node_update, "meshtastic.node.updated")
                pub.unsubscribe(self._on_connection_lost, "meshtastic.connection.lost")
            except Exception:  # noqa: BLE001
                pass
            self._iface.close()
            self._iface = None
