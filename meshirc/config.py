import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class ConfigError(Exception):
    pass


@dataclass
class ConnectionConfig:
    transport: str = "tcp"
    host: str = "192.168.100.38"
    port: int = 4403


@dataclass
class UIConfig:
    sidebar_default: bool = False
    scrollback: int = 2000
    timestamp_format: str = "%H:%M"


@dataclass
class BehaviorConfig:
    mention_words: list[str] = field(default_factory=list)
    auto_open_dm: bool = True


@dataclass
class Config:
    connection: ConnectionConfig = field(default_factory=ConnectionConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    behavior: BehaviorConfig = field(default_factory=BehaviorConfig)


def _check_type(value: Any, expected: type, dotted: str) -> None:
    # bool is subclass of int — guard explicitly
    if expected is int and isinstance(value, bool):
        raise ConfigError(f"{dotted} must be int, got bool")
    if expected is bool and not isinstance(value, bool):
        raise ConfigError(f"{dotted} must be bool, got {type(value).__name__}")
    if not isinstance(value, expected):
        raise ConfigError(
            f"{dotted} must be {expected.__name__}, got {type(value).__name__}"
        )


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


def load_config(
    path: Path | None = None,
    *,
    host_override: str | None = None,
    port_override: int | None = None,
) -> Config:
    cfg_path = path if path is not None else default_path()
    cfg = Config()

    if cfg_path.exists():
        with cfg_path.open("rb") as f:
            raw = tomllib.load(f)
        if "connection" in raw:
            cfg.connection = _coerce_section(
                raw["connection"], ConnectionConfig, "connection"
            )
        if "ui" in raw:
            cfg.ui = _coerce_section(raw["ui"], UIConfig, "ui")
        if "behavior" in raw:
            cfg.behavior = _coerce_section(raw["behavior"], BehaviorConfig, "behavior")

    if host_override is not None:
        cfg.connection.host = host_override
    if port_override is not None:
        cfg.connection.port = port_override

    return cfg
