import asyncio
import difflib
from datetime import datetime
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Header, Input

from meshirc.config import Config
from meshirc.core.commands import (
    BuffersCmd,
    ClearCmd,
    CloseCmd,
    Command,
    CompletionContext,
    ConnectCmd,
    HelpCmd,
    JoinCmd,
    MeCmd,
    MsgCmd,
    NodesCmd,
    ParseError,
    QueryCmd,
    QuitCmd,
    SendCmd,
    WinCmd,
    complete,
    parse,
)
from meshirc.core.models import BufferKind, Message
from meshirc.core.router import BufferRouter
from meshirc.transport.base import Transport
from meshirc.transport.events import Disconnect, NodeUpdate, TextMessage
from meshirc.ui.widgets.buffer_list import BufferList
from meshirc.ui.widgets.buffer_view import BufferView
from meshirc.ui.widgets.input_line import InputLine
from meshirc.ui.widgets.status_bar import StatusBar

COMMANDS = [
    "/help", "/quit", "/msg", "/me", "/win", "/w", "/buffers", "/buf",
    "/join", "/close", "/clear", "/connect", "/nodes", "/query", "/q",
]


class MeshircApp(App[None]):
    CSS_PATH = Path(__file__).parent / "styles.tcss"

    BINDINGS = [
        Binding("ctrl+c", "quit", "quit", show=False),
        Binding("alt+b", "toggle_sidebar", "sidebar"),
        Binding("alt+left", "prev_buffer", "prev"),
        Binding("alt+right", "next_buffer", "next"),
        *[
            Binding(f"alt+{i}", f"select_buffer({i})", f"win {i}", show=False)
            for i in range(1, 10)
        ],
    ]

    def __init__(self, transport: Transport, config: Config) -> None:
        super().__init__()
        self._transport = transport
        self._config = config
        self._router: BufferRouter | None = None
        self._active_index = 0
        self._queue: asyncio.Queue[TextMessage | NodeUpdate | Disconnect] = (
            asyncio.Queue()
        )
        self._loop: asyncio.AbstractEventLoop | None = None
        self._consume_task: asyncio.Task[None] | None = None

    # ---- composition ----------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main"):
            yield BufferList()
            yield BufferView(ts_format=self._config.ui.timestamp_format)
        yield StatusBar()
        yield InputLine(completion_fn=self._completion_fn)

    async def on_mount(self) -> None:
        self._loop = asyncio.get_running_loop()
        self.title = "meshirc"
        self.sub_title = f"connecting to {self._config.connection.host}..."

        try:
            await asyncio.get_running_loop().run_in_executor(
                None, self._transport.start, self._post_event
            )
        except Exception as e:  # noqa: BLE001
            self.sub_title = f"connect failed: {e}"
            return

        self._router = BufferRouter(
            my_node_id=self._transport.my_node_id,
            my_node_num=self._transport.my_node_num,
            my_short_name=self._transport.my_short_name,
        )
        for idx, name in self._transport.list_channels().items():
            self._router.ensure_channel(idx, name)
        for n in self._transport.list_nodes():
            num = int(n.node_id[1:], 16) if n.node_id.startswith("!") else 0
            self._router.on_node_seen(num, n.long_name, n.short_name, n.last_heard)
        self._router.on_system(f"connected to {self._config.connection.host}")

        if self._config.ui.sidebar_default:
            self._sidebar.add_class("visible")

        self._active_index = 1 if len(self._router.buffers()) > 1 else 0
        self._refresh_all()
        self.sub_title = f"node:{self._transport.my_node_id}"

        self._consume_task = asyncio.create_task(self._consume_events())

    # ---- event flow -----------------------------------------------------

    def _post_event(self, evt: TextMessage | NodeUpdate | Disconnect) -> None:
        """Called from meshtastic worker thread — must be thread-safe."""
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._queue.put_nowait, evt)

    async def _consume_events(self) -> None:
        assert self._router is not None
        while True:
            evt = await self._queue.get()
            if isinstance(evt, TextMessage):
                buf = self._router.on_text(evt)
                if buf is not None:
                    bufs = self._router.buffers()
                    if bufs[self._active_index] is buf:
                        self._buffer_view.append_message(buf.messages[-1])
                        buf.mark_read()
                    self._refresh_status()
            elif isinstance(evt, NodeUpdate):
                num = int(evt.node_id[1:], 16) if evt.node_id.startswith("!") else 0
                self._router.on_node_seen(
                    num, evt.long_name, evt.short_name, evt.last_heard
                )
            elif isinstance(evt, Disconnect):
                self._router.on_system(f"disconnected: {evt.reason}")
                self._refresh_active()

    # ---- input handling -------------------------------------------------

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        line = event.value
        self._input.value = ""
        self._input.push_history(line)
        if self._router is None:
            return
        try:
            cmd = parse(line)
        except ParseError as e:
            self._router.on_system(str(e))
            self._refresh_active()
            return
        await self._dispatch(cmd)

    async def _dispatch(self, cmd: Command) -> None:
        assert self._router is not None
        bufs = self._router.buffers()
        active = bufs[self._active_index]

        match cmd:
            case QuitCmd():
                self.exit()
            case HelpCmd():
                self._router.on_system("commands: " + " ".join(COMMANDS))
                self._refresh_active()
            case WinCmd(index=i):
                if 1 <= i <= len(bufs):
                    self._select_buffer(i - 1)
                else:
                    self._router.on_system(f"no buffer #{i}")
                    self._refresh_active()
            case BuffersCmd():
                self.action_toggle_sidebar()
            case CloseCmd():
                if active.kind == BufferKind.DM and isinstance(active.target, str):
                    self._router.close_dm(active.target)
                    self._active_index = max(0, self._active_index - 1)
                    self._refresh_all()
                else:
                    self._router.on_system("cannot close console or channel")
                    self._refresh_active()
            case ClearCmd():
                active.messages.clear()
                self._refresh_active()
            case NodesCmd():
                for n in self._transport.list_nodes():
                    self._router.on_system(
                        f"  {n.short_name:8s} {n.long_name} {n.node_id}"
                    )
                self._refresh_active()
            case MeCmd(text=t):
                await self._send_to_active(f"* {self._transport.my_short_name} {t}")
            case ConnectCmd(host=h):
                self._router.on_system(
                    f"reconnect not implemented in MVP (host={h})"
                )
                self._refresh_active()
            case MsgCmd(target=tgt, text=text):
                node_id = self._resolve_target(tgt)
                if node_id is None:
                    return
                buf = self._router.get_or_create_dm(node_id)
                self._active_index = self._router.buffers().index(buf)
                await self._send_dm(node_id, text)
                self._refresh_all()
            case QueryCmd(target=tgt):
                node_id = self._resolve_target(tgt)
                if node_id is None:
                    return
                buf = self._router.get_or_create_dm(node_id)
                self._active_index = self._router.buffers().index(buf)
                self._refresh_all()
            case JoinCmd(target=tgt):
                idx = self._resolve_channel(tgt)
                if idx is None:
                    return
                self._select_buffer(idx)
            case SendCmd(text=t):
                if t == "":
                    return
                await self._send_to_active(t)

    # ---- send helpers ---------------------------------------------------

    async def _send_to_active(self, text: str) -> None:
        assert self._router is not None
        bufs = self._router.buffers()
        active = bufs[self._active_index]
        if active.kind == BufferKind.CONSOLE:
            self._router.on_system("console is read-only — use /msg or /win")
            self._refresh_active()
            return
        if active.kind == BufferKind.CHANNEL and isinstance(active.target, int):
            await self._send_channel(active.target, text)
        elif active.kind == BufferKind.DM and isinstance(active.target, str):
            await self._send_dm(active.target, text)

    async def _send_channel(self, channel_idx: int, text: str) -> None:
        assert self._router is not None
        loop = asyncio.get_running_loop()
        try:
            packet_id = await loop.run_in_executor(
                None, lambda: self._transport.send_text(text, channel=channel_idx)
            )
        except Exception as e:  # noqa: BLE001
            self._router.on_system(f"send failed: {e}")
            self._refresh_active()
            return
        self._router.record_local_echo(packet_id)
        buf = self._router.ensure_channel(channel_idx)
        buf.append(Message(ts=datetime.now(), from_id="me", text=text))
        if self._router.buffers()[self._active_index] is buf:
            self._buffer_view.append_message(buf.messages[-1])
            buf.mark_read()
        self._refresh_status()

    async def _send_dm(self, node_id: str, text: str) -> None:
        assert self._router is not None
        loop = asyncio.get_running_loop()
        try:
            packet_id = await loop.run_in_executor(
                None, lambda: self._transport.send_text(text, dest_id=node_id)
            )
        except Exception as e:  # noqa: BLE001
            self._router.on_system(f"send failed: {e}")
            self._refresh_active()
            return
        self._router.record_local_echo(packet_id)
        buf = self._router.get_or_create_dm(node_id)
        buf.append(Message(ts=datetime.now(), from_id="me", text=text))
        if self._router.buffers()[self._active_index] is buf:
            self._buffer_view.append_message(buf.messages[-1])
            buf.mark_read()
        self._refresh_status()

    # ---- resolution helpers ---------------------------------------------

    def _resolve_target(self, query: str) -> str | None:
        assert self._router is not None
        if query.startswith("!"):
            return query
        nodes = list(self._router._nodes.values())  # noqa: SLF001
        for n in nodes:
            if n.short_name.lower() == query.lower():
                return n.id
        for n in nodes:
            if n.long_name.lower() == query.lower():
                return n.id
        names = [n.short_name for n in nodes]
        suggestion = difflib.get_close_matches(query, names, n=1)
        hint = f" (did you mean: {suggestion[0]}?)" if suggestion else ""
        self._router.on_system(f"no such node: {query}{hint}")
        self._refresh_active()
        return None

    def _resolve_channel(self, query: str) -> int | None:
        assert self._router is not None
        bufs = self._router.buffers()
        if query.isdigit():
            idx_global = int(query)
            if 1 <= idx_global <= len(bufs):
                return idx_global - 1
        for i, buf in enumerate(bufs):
            if buf.kind == BufferKind.CHANNEL and buf.name.lower() == query.lower():
                return i
        self._router.on_system(f"no such channel: {query}")
        self._refresh_active()
        return None

    # ---- actions --------------------------------------------------------

    def action_toggle_sidebar(self) -> None:
        self._sidebar.toggle()
        self._refresh_status()

    def action_select_buffer(self, n: int) -> None:
        self._select_buffer(n - 1)

    def action_prev_buffer(self) -> None:
        if self._router and self._active_index > 0:
            self._select_buffer(self._active_index - 1)

    def action_next_buffer(self) -> None:
        if self._router and self._active_index < len(self._router.buffers()) - 1:
            self._select_buffer(self._active_index + 1)

    def _select_buffer(self, index: int) -> None:
        if self._router is None:
            return
        bufs = self._router.buffers()
        if not 0 <= index < len(bufs):
            return
        self._active_index = index
        self._refresh_all()
        bufs[index].mark_read()
        self._refresh_status()

    # ---- refresh helpers ------------------------------------------------

    @property
    def _sidebar(self) -> BufferList:
        return self.query_one(BufferList)

    @property
    def _buffer_view(self) -> BufferView:
        return self.query_one(BufferView)

    @property
    def _status_bar(self) -> StatusBar:
        return self.query_one(StatusBar)

    @property
    def _input(self) -> InputLine:
        return self.query_one(InputLine)

    def _refresh_all(self) -> None:
        if self._router is None:
            return
        bufs = self._router.buffers()
        active = bufs[self._active_index]
        self._buffer_view.set_buffer(active)
        self._input.set_prompt(f"{active.name}> ")
        self._refresh_status()

    def _refresh_active(self) -> None:
        if self._router is None:
            return
        bufs = self._router.buffers()
        if not bufs:
            return
        self._buffer_view.set_buffer(bufs[self._active_index])
        self._refresh_status()

    def _refresh_status(self) -> None:
        if self._router is None:
            return
        bufs = self._router.buffers()
        self._status_bar.update_state(bufs, self._active_index)
        self._sidebar.update_state(bufs, self._active_index)

    # ---- completion -----------------------------------------------------

    def _completion_fn(self, line: str, cursor: int) -> list[str]:
        if self._router is None:
            return []
        nodes_pool: list[str] = []
        for n in self._router._nodes.values():  # noqa: SLF001
            nodes_pool.append(n.short_name)
            nodes_pool.append(n.id)
        bufs = self._router.buffers()
        channels_pool = [b.name for b in bufs if b.kind == BufferKind.CHANNEL]
        active = bufs[self._active_index]
        recent: list[str] = []
        for m in reversed(active.messages):
            if m.from_id not in ("me", "system") and m.from_id not in recent:
                recent.append(m.from_id)
            if len(recent) >= 20:
                break
        ctx = CompletionContext(
            commands=COMMANDS,
            nodes=nodes_pool,
            channels=channels_pool,
            recent_in_buffer=recent,
        )
        return complete(line, cursor, ctx)
