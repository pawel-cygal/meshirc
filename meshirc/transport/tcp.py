import meshtastic.tcp_interface

from meshirc.transport.common import MeshtasticInterfaceTransport


class MeshtasticTcpTransport(MeshtasticInterfaceTransport):
    def __init__(self, host: str, port: int = 4403) -> None:
        super().__init__()
        self.host = host
        self.port = port

    @property
    def target_label(self) -> str:
        return f"{self.host}:{self.port}"

    def _connect(self) -> meshtastic.tcp_interface.TCPInterface:
        return meshtastic.tcp_interface.TCPInterface(
            hostname=self.host, portNumber=self.port, timeout=8
        )

    def _update_target(self, target: str) -> None:
        if ":" not in target:
            self.host = target
            return
        host, port = target.rsplit(":", 1)
        self.host = host
        self.port = int(port)
