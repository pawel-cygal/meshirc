from textual.widgets import Static

from meshirc.core.models import Buffer


class StatusBar(Static):
    """Shows numbered list of buffers with state indicators."""

    def update_state(self, buffers: list[Buffer], active_index: int) -> None:
        parts: list[str] = []
        for i, buf in enumerate(buffers, start=1):
            if buf.has_mention:
                sep = "*"
            elif buf.unread > 0 and i - 1 != active_index:
                sep = ":"
            else:
                sep = "."
            label = f"{i}{sep}{buf.name}"
            if i - 1 == active_index:
                parts.append(f"[reverse]{label}[/reverse]")
            else:
                parts.append(label)
        self.update(" ".join(parts))
