import meshtastic.serial_interface

from meshirc.transport.common import MeshtasticInterfaceTransport


class MeshtasticSerialTransport(MeshtasticInterfaceTransport):
    def __init__(self, device: str | None = None) -> None:
        super().__init__()
        self.device = device or ""

    @property
    def target_label(self) -> str:
        return self.device or "auto serial"

    def _connect(self) -> meshtastic.serial_interface.SerialInterface:
        return meshtastic.serial_interface.SerialInterface(devPath=self.device or None, timeout=8)

    def _update_target(self, target: str) -> None:
        self.device = target
