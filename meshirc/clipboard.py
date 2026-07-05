from __future__ import annotations

import os
import shutil
import subprocess


def copy_to_system_clipboard(text: str) -> str | None:
    for command in _copy_commands():
        if shutil.which(command[0]) is None:
            continue
        try:
            subprocess.run(
                command,
                input=text,
                text=True,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (OSError, subprocess.CalledProcessError):
            continue
        return command[0]

    return _copy_with_tk(text)


def get_system_clipboard() -> str | None:
    for command in _paste_commands():
        if shutil.which(command[0]) is None:
            continue
        try:
            result = subprocess.run(
                command,
                text=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        except (OSError, subprocess.CalledProcessError):
            continue
        return result.stdout

    return _get_with_tk()


def _copy_commands() -> list[list[str]]:
    if os.environ.get("WAYLAND_DISPLAY"):
        return [
            ["wl-copy"],
            ["xclip", "-selection", "clipboard"],
            ["xsel", "--clipboard", "--input"],
        ]
    return [
        ["xclip", "-selection", "clipboard"],
        ["xsel", "--clipboard", "--input"],
        ["wl-copy"],
    ]


def _paste_commands() -> list[list[str]]:
    if os.environ.get("WAYLAND_DISPLAY"):
        return [
            ["wl-paste", "--no-newline"],
            ["xclip", "-selection", "clipboard", "-out"],
            ["xsel", "--clipboard", "--output"],
        ]
    return [
        ["xclip", "-selection", "clipboard", "-out"],
        ["xsel", "--clipboard", "--output"],
        ["wl-paste", "--no-newline"],
    ]


def _copy_with_tk(text: str) -> str | None:
    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        root.destroy()
    except Exception:  # noqa: BLE001
        return None
    return "tkinter"


def _get_with_tk() -> str | None:
    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        text = root.clipboard_get()
        root.destroy()
    except Exception:  # noqa: BLE001
        return None
    return text
