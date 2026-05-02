from collections import deque
from collections.abc import Callable

from textual import events
from textual.widgets import Input

CompletionFn = Callable[[str, int], list[str]]


class InputLine(Input):
    """Input with prompt prefix, command history, and tab completion."""

    def __init__(self, completion_fn: CompletionFn) -> None:
        super().__init__(placeholder="")
        self._completion = completion_fn
        self._history: deque[str] = deque(maxlen=200)
        self._history_pos: int | None = None
        self._draft: str = ""

    def set_prompt(self, prompt: str) -> None:
        self.placeholder = prompt

    def push_history(self, line: str) -> None:
        if line:
            self._history.append(line)
        self._history_pos = None
        self._draft = ""

    async def _on_key(self, event: events.Key) -> None:
        if event.key == "tab":
            event.prevent_default()
            event.stop()
            candidates = self._completion(self.value, self.cursor_position)
            if len(candidates) == 1:
                self._apply_completion(candidates[0])
            elif len(candidates) > 1:
                self.app.bell()
        elif event.key == "up":
            event.prevent_default()
            event.stop()
            self._history_back()
        elif event.key == "down":
            event.prevent_default()
            event.stop()
            self._history_forward()

    def _apply_completion(self, candidate: str) -> None:
        line = self.value
        cursor = self.cursor_position
        head = line[:cursor]
        tail = line[cursor:]
        for sep in (" /msg ", " /query ", " /q ", " /join ", " "):
            idx = head.rfind(sep)
            if idx != -1:
                start = idx + len(sep)
                break
        else:
            at = head.rfind("@")
            start = at + 1 if at != -1 else 0
        new_head = head[:start] + candidate
        self.value = new_head + tail
        self.cursor_position = len(new_head)

    def _history_back(self) -> None:
        if not self._history:
            return
        if self._history_pos is None:
            self._draft = self.value
            self._history_pos = len(self._history) - 1
        elif self._history_pos > 0:
            self._history_pos -= 1
        self.value = self._history[self._history_pos]
        self.cursor_position = len(self.value)

    def _history_forward(self) -> None:
        if self._history_pos is None:
            return
        if self._history_pos < len(self._history) - 1:
            self._history_pos += 1
            self.value = self._history[self._history_pos]
        else:
            self._history_pos = None
            self.value = self._draft
        self.cursor_position = len(self.value)
