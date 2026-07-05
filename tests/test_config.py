from pathlib import Path

import pytest

from meshirc.config import ConfigError, load_config


def test_defaults_when_file_missing(tmp_path: Path):
    cfg = load_config(path=tmp_path / "missing.toml")
    assert cfg.connection.transport == "serial"
    assert cfg.connection.host == "127.0.0.1"
    assert cfg.connection.port == 4403
    assert cfg.connection.serial_device == ""
    assert cfg.ui.sidebar_default is True
    assert cfg.ui.scrollback == 2000
    assert cfg.ui.timestamp_format == "%H:%M"
    assert cfg.behavior.mention_words == []
    assert cfg.behavior.auto_open_dm is True
    assert cfg.archive.enabled is True
    assert cfg.archive.path == ""


def test_load_full_config(tmp_path: Path):
    p = tmp_path / "c.toml"
    p.write_text("""
[connection]
transport = "serial"
host = "10.0.0.5"
port = 4403
serial_device = "/dev/ttyUSB0"

[ui]
sidebar_default = true
scrollback = 500
timestamp_format = "%H:%M:%S"

[behavior]
mention_words = ["alarm", "halt"]
auto_open_dm = false

[archive]
enabled = false
path = "/tmp/meshirc.sqlite3"
""")
    cfg = load_config(path=p)
    assert cfg.connection.transport == "serial"
    assert cfg.connection.host == "10.0.0.5"
    assert cfg.connection.serial_device == "/dev/ttyUSB0"
    assert cfg.ui.sidebar_default is True
    assert cfg.ui.scrollback == 500
    assert cfg.behavior.mention_words == ["alarm", "halt"]
    assert cfg.behavior.auto_open_dm is False
    assert cfg.archive.enabled is False
    assert cfg.archive.path == "/tmp/meshirc.sqlite3"


def test_partial_config_uses_defaults_for_missing(tmp_path: Path):
    p = tmp_path / "c.toml"
    p.write_text('[connection]\nhost = "1.2.3.4"\n')
    cfg = load_config(path=p)
    assert cfg.connection.host == "1.2.3.4"
    assert cfg.connection.port == 4403
    assert cfg.ui.scrollback == 2000


def test_wrong_type_raises(tmp_path: Path):
    p = tmp_path / "c.toml"
    p.write_text('[ui]\nscrollback = "abc"\n')
    with pytest.raises(ConfigError, match="ui.scrollback"):
        load_config(path=p)


def test_cli_overrides_apply(tmp_path: Path):
    cfg = load_config(
        path=tmp_path / "x.toml",
        host_override="9.9.9.9",
        port_override=5000,
        transport_override="tcp",
    )
    assert cfg.connection.host == "9.9.9.9"
    assert cfg.connection.port == 5000
    assert cfg.connection.transport == "tcp"


def test_serial_override_selects_serial_transport(tmp_path: Path):
    cfg = load_config(path=tmp_path / "x.toml", serial_device_override="/dev/ttyACM0")
    assert cfg.connection.transport == "serial"
    assert cfg.connection.serial_device == "/dev/ttyACM0"


def test_invalid_transport_raises(tmp_path: Path):
    p = tmp_path / "c.toml"
    p.write_text('[connection]\ntransport = "ble"\n')
    with pytest.raises(ConfigError, match="connection.transport"):
        load_config(path=p)


def test_unknown_top_level_key_ignored(tmp_path: Path):
    p = tmp_path / "c.toml"
    p.write_text('[bogus]\nx = 1\n[connection]\nhost = "h"\n')
    cfg = load_config(path=p)
    assert cfg.connection.host == "h"
