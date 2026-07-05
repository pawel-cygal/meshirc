from textual.widgets import ListItem, ListView, Static

from meshirc.core.models import Buffer, BufferKind


class BufferList(ListView):
    """Toggleable sidebar listing buffers."""

    def update_state(self, buffers: list[Buffer], active_index: int) -> None:
        self.clear()
        last_group = ""
        for i, buf in enumerate(buffers, start=1):
            group = self._group_name(buf)
            if group != last_group:
                self.append(ListItem(Static(f"[dim]{group}[/dim]"), disabled=True))
                last_group = group

            if buf.has_mention:
                marker = "*"
            elif buf.unread > 0 and i - 1 != active_index:
                marker = ":"
            else:
                marker = " "
            label = f"[{i}] {marker} {buf.name}"
            item = ListItem(Static(label))
            item.buffer_index = i - 1
            if i - 1 == active_index:
                item.add_class("active")
            self.append(item)

    def _group_name(self, buf: Buffer) -> str:
        if buf.kind == BufferKind.CONSOLE:
            return "Status"
        if buf.kind == BufferKind.CHANNEL:
            return "Channels"
        return "DMs"

    def focus_buffer(self, buffer_index: int) -> None:
        for idx, item in enumerate(self.children):
            if getattr(item, "buffer_index", None) == buffer_index:
                self.index = idx
                return

    def toggle(self) -> bool:
        """Toggle visibility. Returns new visible state."""
        if self.has_class("visible"):
            self.remove_class("visible")
            return False
        self.add_class("visible")
        return True
