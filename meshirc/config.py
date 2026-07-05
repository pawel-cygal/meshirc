import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class ConfigError(Exception):
    pass


@dataclass
class ConnectionConfig:
    transport: str = "serial"
    host: str = "127.0.0.1"
    port: int = 4403
    serial_device: str = ""


@dataclass
class UIConfig:
    sidebar_default: bool = True
    scrollback: int = 2000
    timestamp_format: str = "%H:%M"


@dataclass
class BehaviorConfig:
    mention_words: list[str] = field(default_factory=list)
    auto_open_dm: bool = True


@dataclass
class ArchiveConfig:
    enabled: bool = True
    path: str = ""


@dataclass
class Config:
    connection: ConnectionConfig = field(default_factory=ConnectionConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    behavior: BehaviorConfig = field(default_factory=BehaviorConfig)
    archive: ArchiveConfig = field(default_factory=ArchiveConfig)


def _check_type(value: Any, expected: type, dotted: str) -> None:
    if expected is int and isinstance(value, bool):
        raise ConfigError(f"{dotted} must be int, got bool")
    if expected is bool and not isinstance(value, bool):
        raise ConfigError(f"{dotted} must be bool, got {type(value).__name__}")
    if not isinstance(value, expected):
        raise ConfigError(f"{dotted} must be {expected.__name__}, got {type(value).__name__}")


def _coerce_section(raw: dict[str, Any], section_cls: type, prefix: str) -> Any:
    inst = section_cls()
    for key, value in raw.items():
        if not hasattr(inst, key):
            continue
        current = getattr(inst, key)
        if isinstance(current, list):
            _check_type(value, list, f"{prefix}.{key}")
        else:
            _check_type(value, type(current), f"{prefix}.{key}")
        setattr(inst, key, value)
    return inst


def default_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "meshirc" / "config.toml"


def default_archive_path() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "meshirc" / "archive.sqlite3"


def load_config(
    path: Path | None = None,
    *,
    host_override: str | None = None,
    port_override: int | None = None,
    transport_override: str | None = None,
    serial_device_override: str | None = None,
) -> Config:
    cfg_path = path if path is not None else default_path()
    cfg = Config()

    if cfg_path.exists():
        with cfg_path.open("rb") as f:
            raw = tomllib.load(f)
        if "connection" in raw:
            cfg.connection = _coerce_section(raw["connection"], ConnectionConfig, "connection")
        if "ui" in raw:
            cfg.ui = _coerce_section(raw["ui"], UIConfig, "ui")
        if "behavior" in raw:
            cfg.behavior = _coerce_section(raw["behavior"], BehaviorConfig, "behavior")
        if "archive" in raw:
            cfg.archive = _coerce_section(raw["archive"], ArchiveConfig, "archive")

    if host_override is not None:
        cfg.connection.host = host_override
    if port_override is not None:
        cfg.connection.port = port_override
    if transport_override is not None:
        cfg.connection.transport = transport_override
    if serial_device_override is not None:
        cfg.connection.serial_device = serial_device_override
        cfg.connection.transport = "serial"

    if cfg.connection.transport not in {"tcp", "serial"}:
        raise ConfigError("connection.transport must be tcp or serial")

    return cfg
