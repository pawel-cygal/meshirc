import argparse
import sys
from pathlib import Path

from meshirc.config import default_path, load_config
from meshirc.transport.tcp import MeshtasticTcpTransport
from meshirc.ui.app import MeshircApp


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="meshirc", description="Profanity-style TUI for Meshtastic"
    )
    parser.add_argument("--config", type=Path, default=None, help="path to config.toml")
    parser.add_argument("--host", type=str, default=None, help="override connection.host")
    parser.add_argument("--port", type=int, default=None, help="override connection.port")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    config_path = args.config if args.config else default_path()
    cfg = load_config(
        path=config_path, host_override=args.host, port_override=args.port
    )

    transport = MeshtasticTcpTransport(host=cfg.connection.host, port=cfg.connection.port)
    app = MeshircApp(transport=transport, config=cfg)
    try:
        app.run()
    finally:
        transport.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
