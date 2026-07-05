from contextlib import suppress
from datetime import datetime
from typing import Any

from pubsub import pub

from meshirc.transport.base import EventHandler
from meshirc.transport.events import BROADCAST_NUM, Disconnect, NodeUpdate, TextMessage


def _node_num_to_id(num: int) -> str:
    return f"!{num:08x}"


class MeshtasticInterfaceTransport:
    """Shared adapter for Meshtastic Python interfaces."""

    def __init__(self) -> None:
        self.my_node_id: str = ""
        self.my_node_num: int = 0
        self.my_short_name: str = ""
        self._iface: Any | None = None
        self._on_event: EventHandler | None = None

    @property
    def target_label(self) -> str:
        raise NotImplementedError

    def _connect(self) -> Any:
        raise NotImplementedError

    def _update_target(self, target: str) -> None:
        raise NotImplementedError

    def start(self, on_event: EventHandler) -> None:
        self._on_event = on_event
        self._iface = self._connect()
        self._load_local_node()
        self._subscribe()

    def reconnect(self, target: str | None = None) -> None:
        if self._on_event is None:
            raise RuntimeError("transport was not started")
        if target:
            self._update_target(target)
        self.close()
        self.start(self._on_event)

    def _load_local_node(self) -> None:
        assert self._iface is not None, "transport not started"
        info = self._iface.getMyNodeInfo() or {}
        self.my_node_num = int(info.get("num", 0))
        self.my_node_id = _node_num_to_id(self.my_node_num) if self.my_node_num else "?"
        user = info.get("user", {}) or {}
        self.my_short_name = user.get("shortName") or "?"

    def _subscribe(self) -> None:
        pub.subscribe(self._on_text_packet, "meshtastic.receive.text")
        pub.subscribe(self._on_node_update, "meshtastic.node.updated")
        pub.subscribe(self._on_connection_lost, "meshtastic.connection.lost")

    def _unsubscribe(self) -> None:
        for handler, topic in (
            (self._on_text_packet, "meshtastic.receive.text"),
            (self._on_node_update, "meshtastic.node.updated"),
            (self._on_connection_lost, "meshtastic.connection.lost"),
        ):
            with suppress(Exception):
                pub.unsubscribe(handler, topic)

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
            if name:
                out[ch_idx] = name if name.startswith("#") else f"#{name}"
            elif ch_idx == 0:
                out[ch_idx] = "#primary"
            else:
                out[ch_idx] = f"#channel-{ch_idx}"
        if 0 not in out:
            out[0] = "#primary"
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
        if self._iface is None:
            return
        self._unsubscribe()
        try:
            self._iface.close()
        finally:
            self._iface = None
