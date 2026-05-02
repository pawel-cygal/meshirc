from textual.widgets import ListItem, ListView, Static

from meshirc.core.models import Buffer


class BufferList(ListView):
    """Toggleable sidebar listing buffers."""

    def update_state(self, buffers: list[Buffer], active_index: int) -> None:
        self.clear()
        for i, buf in enumerate(buffers, start=1):
            if buf.has_mention:
                marker = "*"
            elif buf.unread > 0 and i - 1 != active_index:
                marker = ":"
            else:
                marker = " "
            label = f"[{i}] {marker} {buf.name}"
            item = ListItem(Static(label))
            if i - 1 == active_index:
                item.add_class("active")
            self.append(item)

    def toggle(self) -> bool:
        """Toggle visibility. Returns new visible state."""
        if self.has_class("visible"):
            self.remove_class("visible")
            return False
        self.add_class("visible")
        return True
