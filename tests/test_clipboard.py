import subprocess

from meshirc import clipboard


def test_copy_to_system_clipboard_uses_xclip_on_x11(monkeypatch):
    calls = []

    monkeypatch.setenv("DISPLAY", ":1")
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setattr(clipboard.shutil, "which", lambda command: command == "xclip")
    monkeypatch.setattr(clipboard, "_copy_with_tk", lambda text: None)

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(clipboard.subprocess, "run", fake_run)

    assert clipboard.copy_to_system_clipboard("hello") == "xclip"
    assert calls[0][0] == ["xclip", "-selection", "clipboard"]
    assert calls[0][1]["input"] == "hello"


def test_copy_to_system_clipboard_falls_back_to_tk(monkeypatch):
    monkeypatch.setattr(clipboard.shutil, "which", lambda command: None)
    monkeypatch.setattr(clipboard, "_copy_with_tk", lambda text: "tkinter")

    assert clipboard.copy_to_system_clipboard("hello") == "tkinter"


def test_get_system_clipboard_uses_xclip_on_x11(monkeypatch):
    monkeypatch.setenv("DISPLAY", ":1")
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setattr(clipboard.shutil, "which", lambda command: command == "xclip")
    monkeypatch.setattr(clipboard, "_get_with_tk", lambda: None)

    def fake_run(command, **kwargs):
        assert command == ["xclip", "-selection", "clipboard", "-out"]
        return subprocess.CompletedProcess(command, 0, stdout="hello")

    monkeypatch.setattr(clipboard.subprocess, "run", fake_run)

    assert clipboard.get_system_clipboard() == "hello"


def test_get_system_clipboard_returns_none_without_backend(monkeypatch):
    monkeypatch.setattr(clipboard.shutil, "which", lambda command: None)
    monkeypatch.setattr(clipboard, "_get_with_tk", lambda: None)

    assert clipboard.get_system_clipboard() is None
