import re
from collections import OrderedDict
from datetime import datetime

from meshirc.core.models import Buffer, BufferKind, Message, Node
from meshirc.transport.events import BROADCAST_NUM, TextMessage


def _node_num_to_id(num: int) -> str:
    return f"!{num:08x}"


class BufferRouter:
    """Routes incoming events to the correct buffer.

    Pure logic — no Textual, no transport. Testable by feeding fake events.
    """

    def __init__(self, my_node_id: str, my_node_num: int, my_short_name: str) -> None:
        self.my_node_id = my_node_id
        self.my_node_num = my_node_num
        self.my_short_name = my_short_name

        self._console = Buffer(kind=BufferKind.CONSOLE, name="console", target=None)
        self._channels: OrderedDict[int, Buffer] = OrderedDict()
        self._dms: OrderedDict[str, Buffer] = OrderedDict()
        self._nodes: dict[str, Node] = {}
        self._num_to_id: dict[int, str] = {my_node_num: my_node_id}

        self._recent_local_echoes: OrderedDict[int, None] = OrderedDict()
        self._echo_max = 64

        self._mention_re = re.compile(
            rf"(?<![A-Za-z0-9_])({re.escape(my_short_name)}|{re.escape(my_node_id)})(?![A-Za-z0-9_])",
            re.IGNORECASE,
        )

    # ---- bookkeeping ----------------------------------------------------

    def ensure_channel(self, idx: int, name: str | None = None) -> Buffer:
        if idx not in self._channels:
            self._channels[idx] = Buffer(
                kind=BufferKind.CHANNEL,
                name=name or f"#chan{idx}",
                target=idx,
            )
        return self._channels[idx]

    def get_or_create_dm(self, node_id: str) -> Buffer:
        if node_id not in self._dms:
            display = self._nodes.get(node_id)
            display_name = display.short_name if display else node_id
            if not display_name.startswith("@"):
                display_name = f"@{display_name}"
            self._dms[node_id] = Buffer(
                kind=BufferKind.DM,
                name=display_name,
                target=node_id,
            )
        return self._dms[node_id]

    def buffers(self) -> list[Buffer]:
        return [self._console, *self._channels.values(), *self._dms.values()]

    def on_node_seen(
        self, num: int, long_name: str, short_name: str, ts: datetime | None = None
    ) -> None:
        node_id = _node_num_to_id(num)
        self._num_to_id[num] = node_id
        self._nodes[node_id] = Node(
            id=node_id, long_name=long_name, short_name=short_name, last_heard=ts
        )

    def resolve_node_id(self, num: int) -> str:
        return self._num_to_id.get(num, _node_num_to_id(num))

    def close_dm(self, node_id: str) -> bool:
        return self._dms.pop(node_id, None) is not None

    # ---- echo dedup -----------------------------------------------------

    def record_local_echo(self, packet_id: int) -> None:
        self._recent_local_echoes[packet_id] = None
        while len(self._recent_local_echoes) > self._echo_max:
            self._recent_local_echoes.popitem(last=False)

    def was_local_echo(self, packet_id: int) -> bool:
        return packet_id in self._recent_local_echoes

    # ---- main entry points ----------------------------------------------

    def on_text(self, evt: TextMessage) -> Buffer | None:
        if self.was_local_echo(evt.packet_id):
            return None

        is_mention = bool(self._mention_re.search(evt.text))

        if evt.to_id == BROADCAST_NUM:
            buf = self.ensure_channel(evt.channel)
        elif evt.from_id == self.my_node_id:
            buf = self.get_or_create_dm(self.resolve_node_id(evt.to_id))
        elif evt.to_id == self.my_node_num:
            buf = self.get_or_create_dm(evt.from_id)
        else:
            buf = self.ensure_channel(evt.channel)

        buf.append(
            Message(ts=evt.ts, from_id=evt.from_id, text=evt.text, is_mention=is_mention)
        )
        return buf

    def on_system(self, text: str) -> None:
        self._console.append(
            Message(ts=datetime.now(), from_id="system", text=text, is_mention=False)
        )
