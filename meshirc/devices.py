from dataclasses import dataclass


@dataclass(frozen=True)
class SerialDevice:
    device: str
    description: str
    hwid: str


def list_serial_devices() -> list[SerialDevice]:
    try:
        from serial.tools import list_ports
    except ImportError:
        return []

    return [
        SerialDevice(
            device=p.device,
            description=p.description or "",
            hwid=p.hwid or "",
        )
        for p in list_ports.comports()
    ]
