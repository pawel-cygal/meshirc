import argparse
import sys
from pathlib import Path

from meshirc.config import default_path, load_config
from meshirc.devices import list_serial_devices
from meshirc.transport.serial import MeshtasticSerialTransport
from meshirc.transport.tcp import MeshtasticTcpTransport
from meshirc.ui.app import MeshircApp


def _print_devices() -> int:
    devices = list_serial_devices()
    if not devices:
        print("no serial devices found")
        return 0
    for dev in devices:
        detail = f" - {dev.description}" if dev.description else ""
        print(f"{dev.device}{detail}")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "devices":
        return _print_devices()

    parser = argparse.ArgumentParser(
        prog="meshirc", description="Profanity-style TUI for Meshtastic"
    )
    parser.add_argument("--config", type=Path, default=None, help="path to config.toml")
    parser.add_argument(
        "--transport", choices=("tcp", "serial"), default=None, help="connection type"
    )
    parser.add_argument("--host", type=str, default=None, help="override connection.host")
    parser.add_argument("--port", type=int, default=None, help="override connection.port")
    parser.add_argument("--serial", type=str, default=None, help="use serial device path")
    parser.add_argument("--list-devices", action="store_true", help="list serial devices")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    if args.list_devices:
        return _print_devices()

    config_path = args.config if args.config else default_path()
    cfg = load_config(
        path=config_path,
        host_override=args.host,
        port_override=args.port,
        transport_override=args.transport,
        serial_device_override=args.serial,
    )

    if cfg.connection.transport == "serial":
        transport = MeshtasticSerialTransport(device=cfg.connection.serial_device or None)
    else:
        transport = MeshtasticTcpTransport(host=cfg.connection.host, port=cfg.connection.port)

    app = MeshircApp(transport=transport, config=cfg)
    try:
        app.run()
    finally:
        transport.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
