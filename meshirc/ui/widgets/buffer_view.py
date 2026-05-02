import hashlib

from textual.widgets import RichLog

from meshirc.core.models import Buffer, Message

_NICK_COLORS = [
    "cyan", "green", "yellow", "magenta", "blue",
    "bright_cyan", "bright_green", "bright_magenta", "bright_blue",
]


def _nick_color(nick: str) -> str:
    h = int(hashlib.md5(nick.encode("utf-8")).hexdigest(), 16)
    return _NICK_COLORS[h % len(_NICK_COLORS)]


class BufferView(RichLog):
    """Displays messages of a single buffer."""

    def __init__(self, ts_format: str = "%H:%M") -> None:
        super().__init__(highlight=False, markup=True, wrap=True, auto_scroll=True)
        self._ts_format = ts_format
        self._current: Buffer | None = None

    def set_buffer(self, buf: Buffer) -> None:
        self._current = buf
        self.clear()
        for m in buf.messages:
            self._render(m)

    def append_message(self, msg: Message) -> None:
        if self._current is None:
            return
        self._render(msg)

    def _render(self, msg: Message) -> None:
        ts = msg.ts.strftime(self._ts_format)
        if msg.from_id == "system":
            self.write(f"[dim]\\[{ts}] -*- {msg.text}[/dim]")
            return
        nick = "me" if msg.from_id == "me" else msg.from_id
        color = "bright_white" if nick == "me" else _nick_color(nick)
        prefix = f"[dim]\\[{ts}][/dim] [{color}]<{nick}>[/{color}]"
        if msg.is_mention:
            self.write(f"{prefix} [bold red]{msg.text}[/bold red]")
        else:
            self.write(f"{prefix} {msg.text}")
